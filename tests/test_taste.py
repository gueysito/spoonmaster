"""Transactional persistence, truthful diffs and user-controlled scope changes."""

import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from spoonmaster.taste import TasteError, TasteStore


def pref(item="ramen", **updates):
    return {
        "item": item,
        "kind": "cuisine",
        "polarity": 1,
        "scope": "tentative",
        "context": {},
        **updates,
    }


class TasteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "plugin-data" / "taste.sqlite3"
        self.store = TasteStore(self.path)

    def enable(self, owner="one"):
        return self.store.control(owner, "enable")["after"]

    def save(self, changes, owner="one"):
        return self.store.feedback(owner, changes, "feedback", self.store.read(owner)["revision"])

    def test_no_storage_before_consent_and_restart_reads_saved_data(self):
        self.assertIsNone(self.store.read("one"))
        self.assertFalse(self.path.parent.exists())
        with self.assertRaisesRegex(TasteError, "storage_not_enabled"):
            self.store.feedback("one", [pref()], "feedback", 0)
        self.assertFalse(self.path.exists())
        self.enable()
        diff = self.save([pref()])
        self.assertEqual(diff["added"][0]["item"], "ramen")
        self.assertEqual(TasteStore(self.path).read("one"), self.store.read("one"))
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_scope_and_diff_preserve_unrelated_preferences(self):
        self.enable()
        first = self.save([pref(), pref("sushi")])
        sushi = first["added"][1]
        diff = self.save([pref(polarity=-1)])
        self.assertEqual(diff["changed"][0]["before"], first["added"][0])
        self.assertEqual(diff["changed"][0]["after"]["polarity"], -1)
        self.assertEqual(self.store.read("one")["prefs"][1], sushi)
        diff = self.save(
            [pref("noise", kind="vibe", scope="situational", context={"occasion": "tired"})]
        )
        self.assertEqual(diff["held_situational"], [diff["added"][0]["id"]])
        with self.assertRaises(TasteError):
            self.save([pref(scope="situational")])

    def test_one_bad_meal_does_not_create_durable_dislike(self):
        self.enable()
        result = self.save([pref(polarity=-1, scope="durable")])
        item = result["added"][0]
        self.assertEqual(item["scope"], "tentative")
        self.assertTrue(result["rejected_inferences"])
        result = self.store.control("one", "confirm", item["id"])
        confirmed = result["after"]["prefs"][0]
        self.assertEqual(confirmed["scope"], "durable")
        self.assertEqual(confirmed["confidence"], "user_confirmed")

    def test_controls_affect_only_selected_owner_and_preference(self):
        self.enable()
        self.enable("two")
        first = self.save([pref(), pref("sushi")])["added"]
        self.save([pref("pizza")], "two")
        other = self.store.read("two")
        result = self.store.control("one", "correct", first[0]["id"], -1)
        self.assertEqual(result["after"]["prefs"][0]["polarity"], -1)
        self.assertEqual(result["after"]["prefs"][1], first[1])
        self.store.control("one", "remove", first[0]["id"])
        self.assertEqual(self.store.read("one")["prefs"], [first[1]])
        self.store.control("one", "pause")
        with self.assertRaisesRegex(TasteError, "storage_not_enabled"):
            self.save([pref()])
        self.store.control("one", "delete")
        self.assertIsNone(self.store.read("one"))
        self.assertEqual(self.store.read("two"), other)
        self.assertNotIn(b"sushi", self.path.read_bytes())

    def test_concurrent_feedback_has_one_winner_and_exact_diff(self):
        revision = self.enable()["revision"]

        def apply(item):
            try:
                return TasteStore(self.path).feedback("one", [pref(item)], "feedback", revision)
            except TasteError as error:
                return str(error)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(apply, ["ramen", "sushi"]))
        self.assertEqual(results.count("profile_changed"), 1)
        winner = next(r for r in results if isinstance(r, dict))
        self.assertEqual(self.store.read("one")["prefs"], winner["added"])

    def test_corrupt_profile_is_not_overwritten_but_can_be_deleted(self):
        self.enable()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute(
                "UPDATE profiles SET data=? WHERE owner=?", (json.dumps({"bad": True}), "one")
            )
            db.commit()
        with self.assertRaises(TasteError):
            self.store.read("one")
        with self.assertRaises(TasteError):
            self.enable()
        self.store.control("one", "delete")
        self.assertIsNone(self.store.read("one"))

    def test_quota_error_rolls_back_whole_batch(self):
        self.enable()
        for offset in range(0, 96, 8):
            self.save([pref(str(i)) for i in range(offset, offset + 8)])
        before = self.store.read("one")
        with self.assertRaisesRegex(TasteError, "profile_full"):
            self.save([pref(str(i)) for i in range(96, 104)])
        self.assertEqual(self.store.read("one"), before)

    def test_storage_failure_never_reports_success(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b"not a SQLite database")
        with self.assertRaisesRegex(TasteError, "storage_unavailable"):
            self.enable()
        self.assertEqual(self.path.read_bytes(), b"not a SQLite database")

"""First-use choices, consent, transactional seeding and one-time reminders."""

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

from spoonmaster.ledger import LedgerStore
from spoonmaster.onboarding import INTRO, REMINDER, Onboarding
from spoonmaster.onboarding_store import OnboardingStore
from spoonmaster.taste import TasteError, TasteStore
from spoonmaster.taste_service import TasteService
from tests.test_taste import pref
from tests.test_taste_service import dm


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "data"
        self.taste = TasteService(lambda: self.path, LedgerStore(), identity=lambda s: None)
        self.flow = Onboarding(self.taste)
        self.taste.bind("chat", "local-cli")
        self.store = OnboardingStore(self.path / "taste.sqlite3")

    def command(self, value):
        return self.flow.command(value, session_id="chat", platform="cli")

    def finish(self):
        self.command("personalize")
        for step in range(1, 7):
            result = self.command(f"pick {step} 1")
        return result

    def test_first_offer_does_not_write_and_does_not_repeat(self):
        result = self.flow.before_turn(session_id="chat", user_message="hello")
        self.assertIn("Personalize my picks", result["context"])
        self.assertIn("Find food now", result["context"])
        self.assertFalse(self.path.exists())
        self.assertIsNone(self.flow.before_turn(session_id="chat", user_message="dinner nearby"))
        self.assertFalse(self.path.exists())

    def test_skip_starts_search_without_profile_and_reminds_once_across_restart(self):
        self.assertIn("Let's find food", self.command("now"))
        self.assertIsNone(self.store.read("local-cli"))
        self.assertEqual(self.flow.selected("chat"), REMINDER)
        restarted = Onboarding(self.taste)
        self.assertIsNone(restarted.selected("chat"))
        self.assertIsNone(restarted.before_turn(session_id="chat", user_message="hello"))

    def test_no_reminder_or_disk_write_before_any_offer_or_choice(self):
        self.assertIsNone(self.flow.selected("chat"))
        self.assertFalse(self.path.exists())

    def test_six_choices_commit_together_and_completion_suppresses_reminder(self):
        self.command("personalize")
        for step in range(1, 6):
            self.command(f"pick {step} 1")
            self.assertIsNone(self.store.read("local-cli"))
        result = self.command("pick 6 1")
        self.assertIn("You're set", result)
        profile = self.store.read("local-cli")
        self.assertEqual(len(profile["prefs"]), 6)
        self.assertTrue(
            all(p["scope"] == "tentative" and p["polarity"] == 1 for p in profile["prefs"])
        )
        self.assertEqual(profile["prefs"][0]["item"], "burger")
        self.assertEqual(profile["prefs"][1]["item"], "ramen")
        self.assertIsNone(self.flow.selected("chat"))
        self.assertEqual(self.store.status("local-cli")["status"], "complete")

    def test_cancel_midway_does_not_enable_or_save_partial_tastes(self):
        self.command("personalize")
        self.command("pick 1 2")
        self.command("now")
        self.assertIsNone(self.store.read("local-cli"))
        self.assertIn("No active questions", self.command("pick 2 1"))

    def test_existing_preferences_remain_unchanged(self):
        store = TasteStore(self.store.path)
        revision = store.control("local-cli", "enable")["after"]["revision"]
        before = store.feedback("local-cli", [pref("ramen", polarity=-1)], "feedback", revision)[
            "added"
        ][0]
        self.finish()
        profile = store.read("local-cli")
        self.assertEqual(next(p for p in profile["prefs"] if p["id"] == before["id"]), before)
        self.assertEqual(len(profile["prefs"]), 6)

    def test_changed_profile_or_deleted_attempt_cannot_be_overwritten(self):
        self.command("personalize")
        for step in range(1, 6):
            self.command(f"pick {step} 1")
        self.taste.command("enable", platform="cli", session_id="chat")
        result = self.command("pick 6 1")
        self.assertIn("profile_changed", result)
        self.assertEqual(self.store.read("local-cli")["prefs"], [])
        self.command("delete confirm")
        self.assertIsNone(self.store.status("local-cli"))
        self.assertIn("No active questions", self.command("pick 6 1"))

    def test_invalid_or_stale_answer_does_not_advance(self):
        self.command("personalize")
        self.assertIn("different question", self.command("pick 3 1"))
        self.assertIn("2/6", self.command("pick 1 2"))
        self.assertIn("different question", self.command("pick 1 2"))
        self.assertEqual(len(self.flow.drafts["chat"]["choices"]), 1)

    def test_direct_phrase_and_plain_answers_work_without_buttons(self):
        intro = self.flow.before_turn(session_id="chat", user_message="get me onboarded")
        self.assertIn(INTRO, intro["context"])
        self.assertIsNone(self.store.read("local-cli"))
        result = self.flow.before_turn(session_id="chat", user_message="personalize my picks")
        self.assertIn("1/6", result["context"])
        for answer in ("pizza", "2", "1", "skip", "2", "1"):
            result = self.flow.before_turn(session_id="chat", user_message=answer)
        self.assertIn("You're set", result["context"])
        self.assertEqual(len(self.store.read("local-cli")["prefs"]), 5)

    def test_buttons_and_unsupported_button_fallback(self):
        self.flow.ask_choice = Mock(side_effect=["personalize", "1", "2", "1", "1", "2", "1"])
        self.assertIn("You're set", self.command("start"))
        self.assertEqual(self.flow.ask_choice.call_count, 7)
        self.flow.ask_choice = Mock(side_effect=RuntimeError("unavailable"))
        self.assertEqual(self.command("start"), INTRO)

    def test_shared_chat_is_denied_and_wrong_user_cannot_answer(self):
        source = dm()
        source.chat_type = "group"
        result = self.flow.command("personalize", source=source, session_id="shared")
        self.assertIn("private chat", result)
        self.assertFalse(self.path.exists())
        self.command("personalize")
        self.taste.bind("chat", "other-person")
        self.assertIn("No active questions", self.flow.answer("chat", 1, "1"))

    def test_reminder_claim_is_atomic_across_instances(self):
        self.command("now")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda _: OnboardingStore(self.store.path).claim_reminder("local-cli"), range(2)
                )
            )
        self.assertEqual(sorted(results), [False, True])

    def test_selected_tool_reminder_only_follows_successful_selection(self):
        self.command("now")

        def handler(args, **kwargs):
            return json.dumps({"error": "venue_not_presented"})

        self.assertNotIn(
            "onboarding_reminder",
            json.loads(self.flow.selection_tool(handler, {}, session_id="chat")),
        )

        def handler(args, **kwargs):
            return json.dumps({"card": {"text": "Selected"}, "proceed": True})

        result = json.loads(self.flow.selection_tool(handler, {}, session_id="chat"))
        self.assertIn(REMINDER, result["card"]["text"])
        self.assertNotIn(
            "onboarding_reminder",
            json.loads(self.flow.selection_tool(handler, {}, session_id="chat")),
        )

    def test_store_failure_does_not_block_search_or_claim_saved_tastes(self):
        from unittest.mock import patch

        with patch.object(OnboardingStore, "skip", side_effect=TasteError("storage_unavailable")):
            self.assertIn("searching still works", self.command("now"))
        self.assertIsNone(self.store.read("local-cli"))

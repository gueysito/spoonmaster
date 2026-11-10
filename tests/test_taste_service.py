"""Future sessions reconnect without exposing one person's tastes to another."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from spoonmaster import plugin
from spoonmaster.ledger import LedgerStore
from spoonmaster.taste import TasteError
from spoonmaster.taste_service import TasteService, owner_key, runtime_owner
from spoonmaster.venue_web import PageError
from spoonmaster.verification import Verifier
from tests.test_gates import SEARCH, venue
from tests.test_taste import pref


def dm(user="one", **updates):
    return SimpleNamespace(
        platform="telegram", chat_type="dm", user_id=user, scope_id="", **updates
    )


class TasteServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledgers = LedgerStore()
        self.identity = None
        self.service = TasteService(
            lambda: self.root, self.ledgers, identity=lambda s: self.identity
        )

    def command(self, value, session="first", source=None, platform="telegram"):
        return self.service.command(
            value, source=source or dm(), platform=platform, session_id=session
        )

    def feedback(self, changes, session="first"):
        profile = json.loads(self.service.profile_tool({}, session_id=session))["profile"]
        return json.loads(
            self.service.feedback_tool(
                {
                    "changes": changes,
                    "provenance": "feedback",
                    "expected_revision": profile["revision"],
                },
                session_id=session,
            )
        )

    def test_opt_in_future_session_and_restart_keep_tastes(self):
        self.command("enable")
        saved = self.feedback([pref()])
        self.assertTrue(saved["saved"])
        self.service.forget("first")
        # Host metadata identifies the same person in a new session, without a reconnect command.
        restarted = TasteService(
            lambda: self.root, self.ledgers, identity=lambda s: owner_key(dm(), None)
        )
        result = json.loads(restarted.profile_tool({}, session_id="new-session"))
        self.assertEqual(result["profile"]["prefs"], saved["diff"]["added"])
        self.assertIn("taste memory", restarted.before_turn(session_id="new-session")["context"])

    def test_profile_is_readable_while_export_and_tool_preserve_data(self):
        self.assertIn("haven't saved any tastes", self.command("profile"))
        self.command("enable")
        self.feedback(
            [
                pref("burger", kind="dish"),
                pref("sushi"),
                pref("crispy", kind="attribute"),
                pref("lively", kind="vibe"),
            ]
        )
        before = json.loads(self.command("export"))["profile"]
        shown = self.command("profile")
        self.assertIn("Your food profile", shown)
        self.assertIn("Food\n- Like: burger", shown)
        self.assertIn("Atmosphere\n- Like: lively", shown)
        self.assertIn("starting preferences", shown)
        for field in ("updated_at", "revision", "reported_once", before["prefs"][0]["id"]):
            self.assertNotIn(field, shown)
        self.assertEqual(json.loads(self.command("export"))["profile"], before)
        self.assertEqual(
            json.loads(self.service.profile_tool({}, session_id="first"))["profile"], before
        )

    def test_profile_preserves_dislike_context_and_paused_status(self):
        self.command("enable")
        self.feedback([pref("ramen", polarity=-1, scope="situational", context={"time": "lunch"})])
        self.command("pause")
        shown = self.command("profile")
        self.assertIn("Taste memory is paused", shown)
        self.assertIn("Prefer to avoid: ramen (time: lunch)", shown)

    def test_identity_swap_shared_chat_and_model_supplied_owner_fail_closed(self):
        self.command("enable")
        self.feedback([pref()])
        self.identity = owner_key(dm("two"), None)
        self.assertIsNone(json.loads(self.service.profile_tool({}, session_id="first"))["profile"])
        self.identity = False  # Current host context is shared or mismatched.
        self.assertEqual(
            json.loads(self.service.profile_tool({}, session_id="first"))["error"],
            "private_context_required",
        )
        self.assertEqual(
            json.loads(self.service.profile_tool({"owner": "one"}, session_id="first"))["error"],
            "invalid_arguments",
        )
        shared = dm()
        shared.chat_type = "group"
        self.assertIn("private chat", self.command("enable", source=shared))
        self.assertIn("private chat", self.service.command("enable", session_id="missing"))

    def test_cli_session_reset_clears_binding_but_not_profile(self):
        self.service.command("enable", platform="cli", session_id="old")
        self.feedback([pref()], session="old")
        self.service.forget("old")
        self.assertIn("context", self.service.before_turn(session_id="new", platform="cli"))
        self.assertEqual(
            json.loads(self.service.profile_tool({}, session_id="new"))["profile"]["prefs"][0][
                "item"
            ],
            "ramen",
        )

    def test_delete_and_export_are_targeted_and_storage_failure_has_no_success(self):
        self.command("enable")
        self.feedback([pref()])
        self.assertIn("ramen", self.command("export"))
        self.assertNotIn("deleted", self.command("delete"))
        self.assertIn("have been deleted", self.command("delete confirm"))
        self.assertEqual(
            json.loads(self.service.profile_tool({}, session_id="first"))["error"],
            "private_context_required",
        )
        self.command("enable")
        with patch(
            "spoonmaster.taste_service.TasteStore.feedback",
            side_effect=TasteError("storage_unavailable"),
        ):
            result = self.feedback([pref()])
        self.assertFalse(result["saved"])
        self.assertNotIn("diff", result)

    def test_feedback_changes_next_pick_and_invalidates_old_choices(self):
        self.command("enable")
        self.feedback([pref("sushi")])
        now = datetime.now(timezone.utc).isoformat()
        venues = [
            venue("osm:node:1", cuisine="ramen", retrieved_at=now),
            venue(
                "osm:node:2",
                name="Other Dining",
                latitude=35.001,
                cuisine="sushi",
                retrieved_at=now,
            ),
        ]
        found = self.ledgers.remember(
            "first", {"candidates": venues, "candidates_in_radius": 2}, SEARCH
        )
        verifier = Verifier(
            fetch=lambda url: (_ for _ in ()).throw(PageError("network_unavailable"))
        )
        verifier.remember(venues)
        with patch.object(plugin, "verifier", verifier):
            result = json.loads(
                plugin.recommend_candidates(
                    {"search_id": found, "origin_confirmed": True},
                    session_id="first",
                    _ledger_store=self.ledgers,
                    _taste_service=self.service,
                )
            )
        self.assertEqual(result["cards"][0]["venue_id"], "osm:node:2")
        self.assertIn("tentative like for sushi", result["cards"][0]["fit"])
        self.feedback([pref("ramen")])
        self.assertIsNotNone(self.ledgers.search("first", found))
        self.assertIsNone(self.ledgers.latest("first"))
        self.assertIsNone(self.ledgers.search("first", found)["presentation"])

    def test_runtime_adapter_uses_task_context_and_rejects_mismatch(self):
        values = {
            "HERMES_SESSION_KEY": "route",
            "HERMES_SESSION_ID": "new",
            "HERMES_SESSION_PLATFORM": "telegram",
            "HERMES_SESSION_CHAT_TYPE": "dm",
            "HERMES_SESSION_USER_ID": "one",
        }
        module = SimpleNamespace(
            bound_session_key=lambda: "route", get_session_env=lambda key: values.get(key, "")
        )
        with patch.dict("sys.modules", {"gateway.session_context": module}):
            self.assertEqual(runtime_owner("new"), owner_key(dm(), None))
            self.assertIs(runtime_owner("other"), False)
            values["HERMES_SESSION_CHAT_TYPE"] = "group"
            self.assertIs(runtime_owner("new"), False)
            values["HERMES_SESSION_CHAT_TYPE"] = "dm"
            values["HERMES_CRON_SESSION"] = "1"
            self.assertIs(runtime_owner("new"), False)

    def test_profile_paths_never_cross_registration_scopes(self):
        self.command("enable")
        self.feedback([pref()])
        second = TasteService(
            lambda: self.root / "other", LedgerStore(), identity=lambda s: owner_key(dm(), None)
        )
        self.assertIsNone(json.loads(second.profile_tool({}, session_id="first"))["profile"])
        self.assertFalse((self.root / "other").exists())

    def test_delete_clears_cached_tastes_even_after_binding_eviction(self):
        self.command("enable")
        self.feedback([pref()])
        search = self.ledgers.remember(
            "first", {"candidates": [], "candidates_in_radius": 0}, SEARCH
        )
        self.ledgers.save(
            "first",
            search,
            {"private_reason": "ramen"},
            taste_scope=self.service.scope("first"),
            taste_revision=self.service.read("first")["revision"],
        )
        self.service.bindings.pop("first")
        self.command("delete confirm", session="new")
        self.assertIsNone(self.ledgers.latest("first"))
        self.assertIsNotNone(self.ledgers.search("first", search))

    def test_another_process_deletion_cannot_leak_old_ledger_on_read(self):
        self.command("enable")
        self.feedback([pref()])
        search = self.ledgers.remember(
            "first", {"candidates": [], "candidates_in_radius": 0}, SEARCH
        )
        self.ledgers.save(
            "first",
            search,
            {"private_reason": "ramen"},
            taste_scope=self.service.scope("first"),
            taste_revision=self.service.read("first")["revision"],
        )
        other = TasteService(lambda: self.root, LedgerStore(), identity=lambda s: None)
        other.command("delete confirm", source=dm(), session_id="other")
        result = json.loads(
            plugin.ledger(
                {}, session_id="first", _ledger_store=self.ledgers, _taste_service=self.service
            )
        )
        self.assertEqual(result["error"], "no_current_ledger")

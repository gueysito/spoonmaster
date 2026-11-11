"""Future sessions reconnect without exposing one person's tastes to another."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from spoonmaster.research_flow import ResearchFlow
from spoonmaster.taste import TasteError
from spoonmaster.taste_service import TasteService, owner_key, runtime_owner
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
        self.identity = None
        self.service = TasteService(lambda: self.root, identity=lambda s: self.identity)

        self.dining = ResearchFlow(None, self.service)
        self.service.invalidate_context = self.dining.invalidate_tastes

    def start(self):
        return json.loads(
            self.dining.start({"location": "Tokyo", "meal": "noodles"}, session_id="first")
        )["request_id"]

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
        restarted = TasteService(lambda: self.root, identity=lambda s: owner_key(dm(), None))
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
        second = TasteService(lambda: self.root / "other", identity=lambda s: owner_key(dm(), None))
        self.assertIsNone(json.loads(second.profile_tool({}, session_id="first"))["profile"])
        self.assertFalse((self.root / "other").exists())

    def test_memory_controls_explain_effect_without_json_and_enable_is_idempotent(self):
        self.assertIn("Taste memory is now on", self.command("enable"))
        before = self.service.read("first")
        response = self.command("enable")
        self.assertIn("already on", response)
        self.assertIn("does not turn restaurant search on or off", response)
        self.assertEqual(before, self.service.read("first"))
        self.assertIn("Food search still works", self.command("pause"))
        self.assertFalse(self.service.read("first")["enabled"])

    def test_feedback_enters_next_request_and_invalidates_old_work(self):
        self.command("enable")
        self.feedback([pref("sushi")])
        self.start()
        self.assertEqual(self.dining.requests["first"]["profile"]["prefs"][0]["item"], "sushi")
        self.feedback([pref("ramen")])
        self.assertNotIn("first", self.dining.requests)

    def test_delete_clears_requests_even_after_binding_eviction(self):
        self.command("enable")
        self.feedback([pref()])
        self.start()
        self.service.bindings.pop("first")
        self.command("delete confirm", session="new")
        self.assertNotIn("first", self.dining.requests)

    def test_other_process_delete_cannot_return_old_reason(self):
        self.command("enable")
        self.feedback([pref()])
        self.start()
        other = TasteService(lambda: self.root, identity=lambda s: None)
        other.command("delete confirm", source=dm(), session_id="other")
        self.assertIn("preferences changed", self.dining.why(session_id="first"))
        self.assertNotIn("first", self.dining.requests)

    def test_identity_swap_without_taste_profiles_cannot_reuse_evidence(self):
        self.command("profile")
        identifier = self.start()
        self.identity = owner_key(dm("two"), None)
        result = json.loads(
            self.dining.research(
                {"request_id": identifier, "tool": "web_search", "arguments_json": "{}"},
                session_id="first",
            )
        )
        self.assertEqual(result["error"], "private_context_changed")

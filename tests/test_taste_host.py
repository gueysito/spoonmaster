"""Exercise the public Hermes identity/data APIs only inside the owned host-test profile."""

import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace

from spoonmaster.ledger import LedgerStore
from spoonmaster.taste_service import TasteService
from tests.test_taste import pref


@unittest.skipUnless(
    Path(os.environ.get("HERMES_HOME", "")).name.startswith("spoonmaster-check-"),
    "Requires scripts/check-hermes.py's owned throwaway profile",
)
class HermesTasteTests(unittest.TestCase):
    def test_real_host_context_reconnects_saved_profile_and_rejects_shared_chat(self):
        from gateway.session_context import clear_session_vars, set_session_vars
        from hermes_cli.plugins_state import PluginState

        state = PluginState("spoonmaster-taste-test")
        home = Path(os.environ["HERMES_HOME"]).resolve()
        self.assertTrue(state.data_dir.resolve().is_relative_to(home))
        service = TasteService(lambda: state.data_dir, LedgerStore())
        source = SimpleNamespace(platform="telegram", chat_type="dm", user_id="synthetic-one")
        result = json.loads(service.command("enable", source=source, session_id="old"))
        revision = result["after"]["revision"]
        args = {"changes": [pref()], "provenance": "feedback", "expected_revision": revision}
        self.assertTrue(json.loads(service.feedback_tool(args, session_id="old"))["saved"])
        service = TasteService(lambda: state.data_dir, LedgerStore())
        tokens = set_session_vars(
            platform="telegram",
            chat_type="dm",
            user_id="synthetic-one",
            session_key="synthetic-route",
            session_id="new",
        )
        try:
            profile = json.loads(service.profile_tool({}, session_id="new"))["profile"]
            self.assertEqual(profile["prefs"][0]["item"], "ramen")
            self.assertIn("context", service.before_turn(session_id="new", platform="telegram"))
            set_session_vars(
                platform="telegram",
                chat_type="group",
                user_id="synthetic-one",
                session_key="synthetic-route",
                session_id="new",
            )
            self.assertEqual(
                json.loads(service.profile_tool({}, session_id="new"))["error"],
                "private_context_required",
            )
        finally:
            clear_session_vars(tokens)
            result = json.loads(
                service.command("delete confirm", source=source, session_id="cleanup")
            )
            self.assertTrue(result["deleted"])

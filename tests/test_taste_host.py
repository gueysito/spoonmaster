"""Exercise the public Hermes identity/data APIs only inside the owned host-test profile."""

import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace

from spoonmaster.companions import CompanionService
from spoonmaster.ledger import LedgerStore
from spoonmaster.locales import LocaleService
from spoonmaster.onboarding import Onboarding
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
            onboarding = Onboarding(service)
            onboarding.command("now", source=source, session_id="new")
            self.assertIsNotNone(onboarding.selected("new"))
            self.assertIsNone(Onboarding(service).selected("new"))
            onboarding.command("personalize", source=source, session_id="new")
            for step in range(1, 7):
                completed = onboarding.command(f"pick {step} 1", source=source, session_id="new")
            self.assertIn("You're set", completed)
            self.assertEqual(len(service.read("new")["prefs"]), 6)
            companions = CompanionService(service)
            preview = json.loads(
                companions.tool(
                    {
                        "action": "prepare",
                        "label": "coworkers",
                        "household": {"members": [{"dietary_restrictions": ["vegan"]}]},
                    },
                    session_id="new",
                )
            )
            saved = json.loads(
                companions.command(
                    preview["confirmation"].removeprefix("/spoon "),
                    source=source,
                    session_id="new",
                )
            )
            self.assertTrue(saved["saved"])
            reconnected = CompanionService(service)
            self.assertEqual(
                json.loads(reconnected.tool({"action": "list"}, session_id="new"))["groups"],
                ["coworkers"],
            )
            # Installed public tool contract, inspected without making a provider call.
            from tools.web_tools import WEB_SEARCH_SCHEMA

            self.assertEqual(WEB_SEARCH_SCHEMA["name"], "web_search")
            self.assertIn("query", WEB_SEARCH_SCHEMA["parameters"]["properties"])
            self.assertIn("limit", WEB_SEARCH_SCHEMA["parameters"]["properties"])
            locale = LocaleService(service)
            loaded = json.loads(
                locale.tool(
                    {"action": "get", "country_code": "JP", "city": "Tokyo"}, session_id="new"
                )
            )
            self.assertEqual(loaded["status"], "bundled")
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
            self.assertEqual(
                json.loads(reconnected.tool({"action": "list"}, session_id="new"))["error"],
                "private_context_required",
            )
            self.assertEqual(
                json.loads(
                    locale.tool(
                        {"action": "get", "country_code": "JP", "city": "Tokyo"}, session_id="new"
                    )
                )["error"],
                "private_context_required",
            )
        finally:
            clear_session_vars(tokens)
            result = json.loads(
                service.command("delete confirm", source=source, session_id="cleanup")
            )
            self.assertTrue(result["deleted"])

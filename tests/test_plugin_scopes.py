"""Exercise the actual entrypoint with two registration scopes and reused conversation IDs."""

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.test_gates import venue


class Context:
    def __init__(self):
        self.tools = {}
        self.commands = {}
        self.hooks = {}

    def register_tool(self, *, name, handler, **kwargs):
        self.tools[name] = handler

    def register_command(self, name, *, handler, **kwargs):
        self.commands[name] = handler

    def register_hook(self, name, handler):
        self.hooks[name] = handler


class RegistrationScopeTests(unittest.TestCase):
    def test_separate_registrations_do_not_share_private_ledgers(self):
        root = Path(__file__).resolve().parents[1]
        name = "spoonmaster_scope_fixture"
        spec = importlib.util.spec_from_file_location(
            name, root / "__init__.py", submodule_search_locations=[str(root)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            first, second = Context(), Context()
            module.register(first)
            module.register(second)
            implementation = sys.modules[name + ".spoonmaster.plugin"]
            data = {"status": "discovery_only", "candidates": [venue()]}
            with patch.object(implementation, "fetch_candidates", return_value=data):
                found = json.loads(
                    first.tools["spoon_candidates"](
                        {"latitude": 35, "longitude": 139}, session_id="reused-session"
                    )
                )
            args = {"search_id": found["search_id"], "origin_confirmed": True}
            first.tools["spoon_evaluate"](args, session_id="reused-session")
            denied = json.loads(second.tools["spoon_recommend"](args, session_id="reused-session"))
            self.assertEqual(denied["error"], "search_not_available")
            denied = json.loads(
                second.tools["spoon_select"](
                    {"search_id": found["search_id"], "venue_id": "osm:node:1"},
                    session_id="reused-session",
                )
            )
            self.assertEqual(denied["error"], "search_not_available")
            other = json.loads(second.tools["spoon_ledger"]({}, session_id="reused-session"))
            self.assertEqual(other, {"error": "no_current_ledger"})
            second.hooks["on_session_reset"](session_id="reused-session")
            self.assertIn("Evaluated 1", first.commands["why"]("", session_id="reused-session"))
            first.hooks["on_session_finalize"](session_id="reused-session")
            self.assertIn(
                "No current dining ledger", first.commands["why"]("", session_id="reused-session")
            )
        finally:
            for key in list(sys.modules):
                if key == name or key.startswith(name + "."):
                    sys.modules.pop(key)

    def test_actual_entrypoint_skip_select_and_later_onboarding(self):
        root = Path(__file__).resolve().parents[1]
        name = "spoonmaster_onboarding_fixture"
        spec = importlib.util.spec_from_file_location(
            name, root / "__init__.py", submodule_search_locations=[str(root)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as temporary:
                context = Context()
                data_dir = Path(temporary) / "data"
                context.state = SimpleNamespace(data_dir=data_dir)
                module.register(context)
                hook = context.hooks["pre_llm_call"]
                result = hook(session_id="first", platform="cli", user_message="hello")
                self.assertIn("Find food now", result["context"])
                self.assertFalse(data_dir.exists())
                self.assertIn(
                    "Let's find food",
                    context.commands["spoon"]("now", session_id="first", platform="cli"),
                )
                implementation = sys.modules[name + ".spoonmaster.plugin"]
                item = venue(retrieved_at=datetime.now(timezone.utc).isoformat(), website=None)
                with patch.object(
                    implementation, "fetch_candidates", return_value={"candidates": [item]}
                ):
                    found = json.loads(
                        context.tools["spoon_candidates"](
                            {"latitude": 35, "longitude": 139}, session_id="first"
                        )
                    )
                result = json.loads(
                    context.tools["spoon_recommend"](
                        {"search_id": found["search_id"], "origin_confirmed": True},
                        session_id="first",
                    )
                )
                self.assertEqual(len(result["cards"]), 1)
                selected = json.loads(
                    context.tools["spoon_select"](
                        {"search_id": found["search_id"], "venue_id": item["venue_id"]},
                        session_id="first",
                    )
                )
                self.assertIn("get me onboarded", selected["onboarding_reminder"])
                self.assertIn(
                    "1/6",
                    hook(session_id="first", platform="cli", user_message="get me onboarded")[
                        "context"
                    ],
                )
                hook(session_id="first", platform="cli", user_message="personalize my picks")
                for _ in range(6):
                    result = hook(session_id="first", platform="cli", user_message="1")
                self.assertIn("You're set", result["context"])
                context.hooks["on_session_reset"](session_id="first")
                result = hook(session_id="later", platform="cli", user_message="hello")
                self.assertNotIn("Welcome to Spoonmaster", result["context"])
                profile = json.loads(context.tools["spoon_profile"]({}, session_id="later"))
                self.assertEqual(len(profile["profile"]["prefs"]), 6)
        finally:
            for key in list(sys.modules):
                if key == name or key.startswith(name + "."):
                    sys.modules.pop(key)

"""Exercise the actual entrypoint with two registration scopes and reused conversation IDs."""

import importlib.util
import json
import sys
import unittest
from pathlib import Path
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

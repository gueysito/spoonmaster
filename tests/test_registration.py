"""Actual package entrypoint, isolated registrations and surviving user workflows."""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tests.test_locales import SOURCES


class Context:
    def __init__(self, directory):
        self.tools, self.commands, self.hooks = {}, {}, {}
        self.state = SimpleNamespace(data_dir=directory)

    def register_tool(self, *, name, handler, schema, **kwargs):
        assert schema["name"] == name
        self.tools[name] = handler

    def register_command(self, name, *, handler, **kwargs):
        self.commands[name] = handler

    def register_hook(self, name, handler):
        self.hooks[name] = handler

    def dispatch_tool(self, name, args, **kwargs):
        return {"url": "https://example.com/menu", "text": "Synthetic menu"}


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(__file__).resolve().parents[1]
        self.name = "spoonmaster_registration_fixture"
        spec = importlib.util.spec_from_file_location(
            self.name, self.root / "__init__.py", submodule_search_locations=[str(self.root)]
        )
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[self.name] = self.module
        spec.loader.exec_module(self.module)
        self.ctx = self.context("first")
        self.ctx.hooks["pre_llm_call"](session_id="s", platform="cli", user_message="hello")

    def tearDown(self):
        for key in list(sys.modules):
            if key == self.name or key.startswith(self.name + "."):
                sys.modules.pop(key)

    def context(self, path):
        ctx = Context(Path(self.temp.name) / path)
        self.module.register(ctx)
        return ctx

    def tool(self, name, args, ctx=None):
        return json.loads((ctx or self.ctx).tools[name](args, session_id="s"))

    def command(self, args):
        return self.ctx.commands["spoon"](args, session_id="s", platform="cli")

    def test_eight_tools_four_hooks_and_registration_has_no_storage_or_network(self):
        self.assertEqual(
            set(self.ctx.tools),
            {
                "spoon_dine",
                "spoon_research",
                "spoon_present",
                "spoon_ledger",
                "spoon_onboard",
                "spoon_profile",
                "spoon_feedback",
                "spoon_companions",
            },
        )
        self.assertEqual(
            set(self.ctx.hooks),
            {"on_session_reset", "on_session_finalize", "pre_llm_call", "transform_llm_output"},
        )
        self.assertFalse(self.ctx.state.data_dir.exists())
        package = Path(self.temp.name) / "fixture_plugin"
        package.mkdir()
        shutil.copy2(self.root / "__init__.py", package)
        shutil.copytree(
            self.root / "spoonmaster",
            package / "spoonmaster",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        before = sorted(str(p) for p in package.rglob("*"))
        script = """
from unittest.mock import patch
with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('unexpected network')):
    import fixture_plugin
    class Context:
        def register_tool(self, **kwargs): print(kwargs['name'])
        def register_command(self, *args, **kwargs): pass
        def register_hook(self, *args, **kwargs): pass
    fixture_plugin.register(Context())
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=self.temp.name,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(result.stdout.split()), set(self.ctx.tools))
        self.assertEqual(before, sorted(str(p) for p in package.rglob("*")))

    def test_registrations_do_not_share_requests_or_reset_one_another(self):
        other = self.context("other")
        started = self.tool("spoon_dine", {"location": "Tokyo", "meal": "noodles"})
        args = {"request_id": started["request_id"], "tool": "web_search", "arguments_json": "{}"}
        self.assertEqual(
            self.tool("spoon_research", args, other)["error"], "request_changed_or_expired"
        )
        other.hooks["on_session_reset"](session_id="s")
        self.assertIn("evidence_id", self.tool("spoon_research", args))
        self.ctx.hooks["on_session_finalize"](session_id="s")
        self.assertEqual(self.tool("spoon_research", args)["error"], "request_changed_or_expired")

    def test_onboarding_still_completes_and_reconnects(self):
        self.assertIn("Let's find you some food", self.command("now"))
        self.command("personalize")
        hook = self.ctx.hooks["pre_llm_call"]
        for _ in range(6):
            result = hook(session_id="s", platform="cli", user_message="1")
        self.assertIn("You're set", result["context"])
        self.ctx.hooks["on_session_reset"](session_id="s")
        hook(session_id="s", platform="cli", user_message="hello")
        self.assertEqual(len(self.tool("spoon_profile", {})["profile"]["prefs"]), 6)

    def test_companion_confirmation_subset_replacement_and_delete(self):
        group = {"members": [{"age": 8, "dietary_restrictions": ["peanut allergy"]}, {"age": 35}]}
        preview = self.tool(
            "spoon_companions", {"action": "prepare", "label": "family", "household": group}
        )
        self.assertTrue(json.loads(self.command(preview["confirmation"][7:]))["saved"])
        request = self.tool("spoon_dine", {"location": "Tokyo", "meal": "noodles"})["request_id"]
        preview = self.tool(
            "spoon_companions",
            {"action": "recall", "label": "family", "members": [1], "request_id": request},
        )
        args = {"request_id": request, "tool": "web_search", "arguments_json": "{}"}
        self.assertIsNone(self.tool("spoon_research", args)["confirmed_party"])
        self.command(preview["confirmation"][7:])
        self.assertEqual(
            self.tool("spoon_research", args)["confirmed_party"]["members"], group["members"][:1]
        )
        request = self.tool("spoon_dine", {"location": "Bali", "meal": "noodles"})["request_id"]
        self.assertIsNone(
            self.tool("spoon_research", {**args, "request_id": request})["confirmed_party"]
        )
        self.command("delete confirm")
        self.assertEqual(
            self.tool("spoon_research", {**args, "request_id": request})["error"],
            "request_changed_or_expired",
        )

    def test_source_management_survives_and_saved_list_guides_research(self):
        preview = self.tool(
            "spoon_profile",
            {
                "action": "sources_propose",
                "country_code": "PT",
                "city": "Lisbon",
                "sources": SOURCES,
            },
        )
        self.assertFalse(self.ctx.state.data_dir.exists())
        self.assertIn("Saved source list", self.command(preview["confirmation"][7:]))
        shown = self.command("locale show PT Lisbon")
        self.assertIn("Synthetic dining guide", shown)
        self.assertNotIn("reviewed_at", shown)
        result = self.tool(
            "spoon_dine",
            {"location": "Lisbon", "city": "Lisbon", "country_code": "PT", "meal": "noodles"},
        )
        self.assertEqual(result["city_source_priorities"], SOURCES)
        self.command("locale forget PT Lisbon")
        self.assertIsNone(
            self.tool(
                "spoon_profile", {"action": "sources_get", "country_code": "PT", "city": "Lisbon"}
            )["saved_city_ladder"]
        )

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
                self.assertIn("Spoonmaster current clock (UTC):", result["context"])
                self.assertIn("Omit expected_arrival", result["context"])
                self.assertIn("location pin", result["context"])
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

    def test_companion_consent_partial_party_and_delete_through_entrypoint(self):
        root = Path(__file__).resolve().parents[1]
        name = "spoonmaster_companion_fixture"
        spec = importlib.util.spec_from_file_location(
            name, root / "__init__.py", submodule_search_locations=[str(root)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as temporary:
                context = Context()
                context.state = SimpleNamespace(data_dir=Path(temporary) / "data")
                module.register(context)
                hook = context.hooks["pre_llm_call"]
                hook(session_id="party", platform="cli", user_message="hello")

                def tool(name, args):
                    return json.loads(context.tools[name](args, session_id="party"))

                def command(value):
                    return context.commands["spoon"](value, session_id="party", platform="cli")

                group = {"members": [{"age": 8}, {"age": 35, "liked_cuisines": ["sushi"]}]}
                preview = tool(
                    "spoon_companions", {"action": "prepare", "label": "family", "household": group}
                )
                self.assertFalse(context.state.data_dir.exists())
                self.assertTrue(
                    json.loads(command(preview["confirmation"].removeprefix("/spoon ")))["saved"]
                )
                implementation = sys.modules[name + ".spoonmaster.plugin"]
                items = [
                    venue(
                        f"osm:node:{n}",
                        name=f"Synthetic dining {n}",
                        cuisine=cuisine,
                        latitude=35 + n / 10000,
                        website=None,
                        household_claims={"min_age": 18},
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                    )
                    for n, cuisine in enumerate(("ramen", "sushi"), 1)
                ]
                with patch.object(
                    implementation, "fetch_candidates", return_value={"candidates": items}
                ):
                    found = tool("spoon_candidates", {"latitude": 35, "longitude": 139})
                search = {"search_id": found["search_id"], "origin_confirmed": True}
                preview = tool(
                    "spoon_companions",
                    {
                        "action": "recall",
                        "label": "family",
                        "members": [1, 2],
                        "search_id": found["search_id"],
                    },
                )
                command(preview["confirmation"].removeprefix("/spoon "))
                result = tool("spoon_recommend", search)
                self.assertEqual(result["cards"], [])
                self.assertIn("member_1.age", context.commands["why"]("", session_id="party"))
                preview = tool(
                    "spoon_companions",
                    {
                        "action": "recall",
                        "label": "family",
                        "members": [2],
                        "search_id": found["search_id"],
                    },
                )
                command(preview["confirmation"].removeprefix("/spoon "))
                result = tool("spoon_recommend", search)
                self.assertEqual(result["cards"][0]["venue_id"], "osm:node:2")
                self.assertIn("Companion 1 likes sushi", result["cards"][0]["fit"])
                chosen = {"search_id": found["search_id"], "venue_id": "osm:node:2"}
                self.assertTrue(tool("spoon_select", chosen)["proceed"])
                self.assertTrue(json.loads(command("delete confirm"))["deleted"])
                self.assertEqual(tool("spoon_select", chosen)["error"], "search_not_available")
                hook(session_id="party", platform="cli", user_message="hello")
                self.assertEqual(tool("spoon_companions", {"action": "list"})["groups"], [])
        finally:
            for key in list(sys.modules):
                if key == name or key.startswith(name + "."):
                    sys.modules.pop(key)

    def test_locale_loader_scout_review_cache_and_delete_through_entrypoint(self):
        root = Path(__file__).resolve().parents[1]
        name = "spoonmaster_locale_fixture"
        spec = importlib.util.spec_from_file_location(
            name, root / "__init__.py", submodule_search_locations=[str(root)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as temporary:
                context = Context()
                context.state = SimpleNamespace(data_dir=Path(temporary) / "data")
                calls = []

                def dispatch(tool, args):
                    calls.append((tool, args))
                    return json.dumps(
                        {
                            "success": True,
                            "data": {
                                "web": [
                                    {
                                        "title": "Synthetic local guide",
                                        "url": "https://example.com/dining",
                                        "description": "Local dining listings and hours.",
                                    }
                                ]
                            },
                        }
                    )

                context.dispatch_tool = dispatch
                module.register(context)
                hook = context.hooks["pre_llm_call"]
                initial = hook(session_id="city", platform="cli", user_message="hello")
                self.assertIn("spoon_locale", initial["context"])

                def call(args, session="city"):
                    return json.loads(context.tools["spoon_locale"](args, session_id=session))

                japan = call({"action": "get", "country_code": "JP", "city": "Tokyo"})
                self.assertEqual(japan["ladder"]["sources"][0]["name"], "Tabelog")
                self.assertFalse(calls)
                scout = call({"action": "scout", "country_code": "PT", "city": "Lisbon"})
                self.assertEqual(len(calls), 2)
                self.assertEqual({name for name, _ in calls}, {"web_search"})
                self.assertFalse(context.state.data_dir.exists())
                result = context.commands["spoon"](
                    scout["confirmation"].removeprefix("/spoon "), platform="cli", session_id="city"
                )
                self.assertTrue(json.loads(result)["saved"])
                context.hooks["on_session_finalize"](session_id="city")
                hook(session_id="later", platform="cli", user_message="hello")
                self.assertEqual(
                    call({"action": "get", "country_code": "PT", "city": "Lisbon"}, "later")[
                        "status"
                    ],
                    "confirmed",
                )
                result = context.commands["spoon"](
                    "delete confirm", platform="cli", session_id="later"
                )
                self.assertTrue(json.loads(result)["deleted"])
                hook(session_id="later", platform="cli", user_message="hello")
                self.assertEqual(
                    call({"action": "get", "country_code": "PT", "city": "Lisbon"}, "later")[
                        "status"
                    ],
                    "scout_needed",
                )
        finally:
            for key in list(sys.modules):
                if key == name or key.startswith(name + "."):
                    sys.modules.pop(key)

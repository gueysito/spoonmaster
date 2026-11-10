"""Exercise the public tool boundary and actual directory-package entrypoint."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spoonmaster import plugin
from spoonmaster.discovery import DiscoveryError
from spoonmaster.ledger import LedgerStore
from spoonmaster.verification import Verifier
from tests.test_discovery import normalized, venue


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch.object(plugin.time, "monotonic", return_value=100)
        self.cooldown = patch.object(plugin, "_next_query_at", 0)
        self.clock.start()
        self.cooldown.start()
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.cooldown.stop)
        self.ledger_store = patch.object(plugin, "ledgers", LedgerStore())
        self.ledger_store.start()
        self.addCleanup(self.ledger_store.stop)

    def test_tool_returns_limited_evidence_and_accepts_host_context(self):
        with patch.object(
            plugin, "fetch_candidates", return_value=normalized([venue(1), venue(2)])
        ):
            result = json.loads(
                plugin.candidates(
                    {"latitude": 0, "longitude": 0, "limit": 1},
                    task_id="synthetic",
                    parent_agent=object(),
                )
            )
        self.assertEqual(result["status"], "discovery_only")
        self.assertEqual(result["candidates_in_radius"], 2)
        self.assertTrue(result["limited"])
        self.assertEqual(result["candidates"][0]["venue_id"], "osm:node:1")
        self.assertEqual(len(result["candidates"]), 1)

    def test_invalid_arguments_never_fetch(self):
        for args in [
            None,
            {"latitude": 0, "longitude": 0, "limit": True},
            {"latitude": 0, "longitude": 0, "url": "http://127.0.0.1"},
            {"latitude": 10**400, "longitude": 0},
            {"latitude": 0, "longitude": 0, "radius_m": -1},
        ]:
            with self.subTest(args=args), patch.object(plugin, "fetch_candidates") as fetch:
                self.assertEqual(
                    json.loads(plugin.candidates(args)), {"error": "invalid_arguments"}
                )
                fetch.assert_not_called()

    def test_missing_location_asks_for_stated_area_or_pin_without_network(self):
        for args in ({}, {"latitude": 35}, {"longitude": 139}):
            with patch.object(plugin, "fetch_candidates") as fetch:
                result = json.loads(plugin.candidates(args))
                self.assertEqual(result["error"], "location_required")
                self.assertIn("location pin", result["action"])
                self.assertIn("landmark", result["action"])
                fetch.assert_not_called()

    def test_failure_remains_unverified_and_cooldown_applies(self):
        with patch.object(
            plugin, "fetch_candidates", side_effect=DiscoveryError("source_rate_limited")
        ):
            first = json.loads(plugin.candidates({"latitude": 0, "longitude": 0}))
            second = json.loads(plugin.candidates({"latitude": 0, "longitude": 0}))
        self.assertEqual(first, {"status": "unverified", "error": "source_rate_limited"})
        self.assertEqual(second["error"], "query_cooldown")
        with patch.object(plugin.time, "monotonic", return_value=111):
            with patch.object(plugin, "fetch_candidates", return_value=normalized([])):
                self.assertEqual(
                    json.loads(plugin.candidates({"latitude": 0, "longitude": 0}))["status"],
                    "discovery_only",
                )

    def test_concurrent_call_is_refused_without_network(self):
        with plugin._query_lock, patch.object(plugin, "fetch_candidates") as fetch:
            result = json.loads(plugin.candidates({"latitude": 0, "longitude": 0}))
        self.assertEqual(result["error"], "query_in_progress")
        fetch.assert_not_called()

    def test_discovery_to_finalists_to_selected_tool_flow(self):
        from tests.test_verification import page
        from tests.test_verification import venue as verification_venue

        data = {"status": "discovery_only", "candidates": [verification_venue()]}
        verifier = Verifier(fetch=lambda url: page())
        with (
            patch.object(plugin, "fetch_candidates", return_value=data),
            patch.object(plugin, "verifier", verifier),
        ):
            discovered = json.loads(plugin.candidates({"latitude": 35, "longitude": 139}))
            ids = [v["venue_id"] for v in discovered["candidates"]]
            finalists = json.loads(plugin.verify_hours({"venue_ids": ids, "stage": "finalists"}))
            selected = json.loads(plugin.verify_hours({"venue_ids": ids, "stage": "selected"}))
        self.assertEqual(finalists["venues"][0]["status"], "confirmed")
        self.assertTrue(selected["venues"][0]["cache_reused"])

    def test_full_search_evaluation_why_and_context_isolation(self):
        from tests.test_gates import venue as gate_venue

        data = {
            "status": "discovery_only",
            "candidates": [gate_venue("osm:node:1"), gate_venue("osm:node:2")],
        }
        with patch.object(plugin, "fetch_candidates", return_value=data):
            found = json.loads(
                plugin.candidates({"latitude": 35, "longitude": 139}, session_id="chat-a")
            )
        args = {
            "search_id": found["search_id"],
            "origin_confirmed": True,
            "excluded_venue_ids": ["osm:node:2"],
        }
        result = json.loads(plugin.evaluate_candidates(args, session_id="chat-a"))
        self.assertEqual(result["evaluated"], 2)
        self.assertEqual(result["counts"]["excluded"], 1)
        self.assertEqual(result["pages"], 2)
        self.assertIn("User explicitly excluded", plugin.why("", session_id="chat-a"))
        second = json.loads(plugin.ledger({"page": 2}, session_id="chat-a"))
        self.assertEqual(second["entries"][0]["venue_id"], "osm:node:2")
        self.assertEqual(
            json.loads(plugin.evaluate_candidates(args, session_id="chat-b"))["error"],
            "search_not_available",
        )
        self.assertEqual(
            json.loads(plugin.ledger({}, session_id="chat-b"))["error"], "no_current_ledger"
        )
        self.assertNotIn("Example Dining", plugin.why("", session_id="chat-b"))
        plugin.forget_session(session_id="chat-a")
        self.assertEqual(
            json.loads(plugin.ledger({}, session_id="chat-a"))["error"], "no_current_ledger"
        )

    def test_ledger_inputs_cannot_supply_identity_or_verdicts(self):
        args = {"search_id": "a" * 24, "origin_confirmed": True}
        for extra in (
            {"session_id": "another-chat"},
            {"verdicts": {"diet": "pass"}},
            {"origin_confirmed": "yes"},
            {"dietary_restrictions": [True]},
            {"excluded_venue_ids": "all"},
            {"expected_arrival": "2026-11-08T10:00"},
        ):
            self.assertEqual(
                json.loads(plugin.evaluate_candidates({**args, **extra}))["error"],
                "invalid_arguments",
            )
        self.assertEqual(
            json.loads(plugin.evaluate_candidates(args))["error"], "conversation_context_required"
        )
        self.assertEqual(json.loads(plugin.ledger({}))["error"], "conversation_context_required")
        for args in ({"session_id": "another-chat"}, {"page": True}, {"page": 21}, []):
            self.assertEqual(json.loads(plugin.ledger(args))["error"], "invalid_arguments")
        for raw in ("0", "-1", "100", "١", "1 extra", "1\n2"):
            self.assertEqual(plugin.why(raw, session_id="chat-a"), "Use /why or /why <page>.")

    def test_directory_entrypoint_registers_without_network_or_storage(self):
        root = Path(__file__).resolve().parents[1]
        # Load under another package name, as Hermes does, with no project on sys.path.
        script = """
import json
from unittest.mock import patch
with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('unexpected network')):
    import fixture_plugin
    class Context:
        def register_tool(self, *, name, toolset, schema, handler):
            assert name == schema['name']
            assert name in ('spoon_dine', 'spoon_onboard', 'spoon_candidates', 'spoon_verify_hours',
                            'spoon_evaluate', 'spoon_ledger', 'spoon_recommend', 'spoon_select',
                            'spoon_profile', 'spoon_feedback', 'spoon_companions', 'spoon_locale')
            assert toolset == 'spoonmaster'
            expected = ('conversation_context_required' if name == 'spoon_ledger'
                        else 'invalid_arguments')
            if name == 'spoon_profile':
                expected = 'private_context_required'
            if name in ('spoon_candidates', 'spoon_dine'):
                expected = 'location_required'
            if name == 'spoon_onboard':
                expected = 'private_context_required'
            assert json.loads(handler({}))['error'] == expected
            print(name)
        def register_command(self, name, handler, description, args_hint):
            assert name in ('why', 'spoon')
            assert handler('')
            print('/' + name)
        def register_hook(self, name, handler):
            assert name in ('on_session_reset', 'on_session_finalize', 'pre_llm_call')
            handler(session_id='synthetic')
    fixture_plugin.register(Context())
"""
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "fixture_plugin"
            package.mkdir()
            shutil.copy2(root / "__init__.py", package)
            shutil.copytree(
                root / "spoonmaster",
                package / "spoonmaster",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            before = sorted(str(path.relative_to(package)) for path in package.rglob("*"))
            result = subprocess.run(
                [sys.executable, "-B", "-c", script],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=10,
            )
            after = sorted(str(path.relative_to(package)) for path in package.rglob("*"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "spoon_dine\nspoon_candidates\nspoon_verify_hours\nspoon_evaluate\nspoon_ledger\nspoon_onboard\nspoon_recommend\nspoon_select\nspoon_profile\nspoon_feedback\nspoon_companions\nspoon_locale\n/spoon\n/why",
        )
        self.assertEqual(before, after)

"""Exercise installed public hook delivery in the script-owned throwaway profile."""

import json
import os
import unittest
from pathlib import Path


@unittest.skipUnless(
    Path(os.environ.get("HERMES_HOME", "")).name.startswith("spoonmaster-check-"),
    "Requires scripts/check-hermes.py's owned throwaway profile",
)
class HermesBrowserHooksTests(unittest.TestCase):
    def test_native_hook_delivery_retains_success_and_rejects_blocked_results(self):
        from hermes_cli.plugins import discover_plugins, get_plugin_manager, invoke_hook
        from tools.registry import registry

        discover_plugins()
        manager = get_plugin_manager()
        context = {"session_id": "synthetic-browser-test", "task_id": "synthetic-task"}
        invoke_hook("pre_llm_call", **context, platform="cli", user_message="Find noodles")

        def tool(name, args):
            return json.loads(registry.dispatch(name, args, scope=manager.scope_key, **context))

        started = tool("spoon_dine", {"location": "Synthetic City", "meal": "noodles"})
        event = {
            **context,
            "tool_name": "browser_exec",
            "tool_call_id": "call-1",
            "turn_id": "turn-1",
            "args": {"session": started["browser_session"], "code": "synthetic; never executed"},
        }
        self.assertEqual(invoke_hook("pre_tool_call", **event), [])
        result = json.dumps(
            {
                "success": True,
                "exit_code": 0,
                "output": "https://example.com/menu\nFresh noodles served daily.",
            }
        )
        self.assertEqual(invoke_hook("post_tool_call", **event, result=result, status="ok"), [])
        collected = tool(
            "spoon_research", {"request_id": started["request_id"], "collect_browser": True}
        )
        evidence = collected["results"][0]
        self.assertEqual(evidence["urls"], ["https://example.com/menu"])
        presented = tool(
            "spoon_present",
            {
                "request_id": started["request_id"],
                "coverage": "One synthetic source.",
                "candidates": [
                    {
                        "name": "Synthetic Noodles",
                        "why": "Public menu evidence.",
                        "evidence": [
                            {
                                "evidence_id": evidence["evidence_id"],
                                "url": "https://example.com/menu",
                                "quote": "Fresh noodles served daily.",
                            }
                        ],
                    }
                ],
            },
        )
        self.assertIn("Synthetic Noodles", presented["text"])
        event["tool_call_id"] = "blocked-call"
        self.assertEqual(invoke_hook("pre_tool_call", **event), [])
        invoke_hook("post_tool_call", **event, result=result, status="blocked")
        self.assertEqual(
            tool("spoon_research", {"request_id": started["request_id"], "collect_browser": True})[
                "results"
            ],
            [],
        )
        invoke_hook("on_session_reset", **context)
        self.assertEqual(
            tool("spoon_research", {"request_id": started["request_id"], "collect_browser": True})[
                "error"
            ],
            "request_changed_or_expired",
        )

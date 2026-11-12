"""Native browser observation cannot turn into an execution or evidence backdoor."""

import json
import unittest
from types import SimpleNamespace

from spoonmaster.research_flow import RESEARCH, ResearchFlow


class BrowserEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.owner = "owner"
        self.party = None
        self.dispatched = []
        self.flow = ResearchFlow(
            lambda *a, **k: self.dispatched.append(a) or "ok",
            SimpleNamespace(read=lambda _: None, scope=lambda _: self.owner),
            clock=lambda: self.now,
        )
        self.flow.party_context = lambda *a: self.party
        self.start()

    def start(self):
        self.started = json.loads(
            self.flow.start(
                {"location": "Synthetic City", "meal": "noodles"}, session_id="s", task_id="task"
            )
        )
        self.event = {
            "tool_name": "browser_exec",
            "args": {"session": self.started["browser_session"], "code": "never executed"},
            "session_id": "s",
            "task_id": "task",
            "tool_call_id": "call",
            "turn_id": "turn",
        }

    def collect(self, **extra):
        return json.loads(
            self.flow.research(
                {"request_id": self.started["request_id"], "collect_browser": True, **extra},
                session_id="s",
                task_id="task",
            )
        )

    def finish(self, event=None, status="ok", **raw):
        result = {
            "success": True,
            "exit_code": 0,
            "output": "https://example.com/menu\nFresh noodles served daily.",
            **raw,
        }
        self.assertIsNone(
            self.flow.after_browser(
                **(event or self.event), status=status, result=json.dumps(result)
            )
        )

    def test_proxy_rejected_in_single_and_every_batch_position_before_dispatch(self):
        props = RESEARCH["parameters"]["properties"]
        self.assertNotIn("browser_exec", props["tool"]["enum"])
        self.assertNotIn("browser_exec", props["batch"]["items"]["properties"]["tool"]["enum"])
        browser = {"tool": "browser_exec", "arguments_json": "{}"}
        search = {"tool": "web_search", "arguments_json": "{}"}
        for body in [
            browser,
            *[{"batch": [search] * i + [browser] + [search] * (2 - i)} for i in range(3)],
        ]:
            result = json.loads(
                self.flow.research(
                    {"request_id": self.started["request_id"], **body}, session_id="s"
                )
            )
            self.assertEqual(result["error"], "unsupported_research_tool")
        self.assertEqual(self.dispatched, [])
        self.assertEqual(self.flow.requests["s"]["calls"], 0)

    def test_observers_return_no_directives_capture_only_output_and_collect_once(self):
        self.assertIsNone(self.flow.before_browser(**self.event))
        self.finish(
            workspace="private-path",
            stderr="private-diagnostic",
            screenshot_path="private-image",
            other="https://metadata.example/secret",
        )
        result = self.collect()
        self.assertEqual(result["results"][0]["evidence_id"], "e1")
        self.assertEqual(result["results"][0]["urls"], ["https://example.com/menu"])
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(self.collect()["results"], [])
        self.assertEqual(self.dispatched, [])
        self.assertIn("e1", self.flow.requests["s"]["evidence"])

    def test_unmatched_and_failed_callbacks_never_become_evidence(self):
        self.finish()
        self.assertEqual(self.collect()["results"], [])
        for status in ["blocked", "cancelled", "error", None]:
            self.start()
            self.flow.before_browser(**self.event)
            self.finish(status=status)
            self.assertEqual(self.collect()["results"], [])
        for raw in [
            {"success": False},
            {"exit_code": 1},
            {"error": "bad"},
            {"output": "no public URL"},
            {"output": "x" * 1000001},
        ]:
            self.start()
            self.flow.before_browser(**self.event)
            self.finish(**raw)
            self.assertEqual(self.collect()["results"], [])

    def test_identity_session_turn_and_task_mismatches_fail_closed(self):
        for change in [
            {"session_id": "other"},
            {"task_id": "other"},
            {"turn_id": ""},
            {"tool_call_id": ""},
            {"tool_name": "terminal"},
            {"args": {"session": "unrelated"}},
        ]:
            self.flow.before_browser(**{**self.event, **change})
        self.assertEqual(self.flow.requests["s"]["calls"], 0)
        self.flow.before_browser(**self.event)
        for change in [
            {"session_id": "other"},
            {"task_id": "other"},
            {"turn_id": "other"},
            {"tool_call_id": "other"},
            {"args": {"session": "unrelated"}},
        ]:
            self.finish(event={**self.event, **change})
            self.assertEqual(self.collect()["results"], [])
        self.owner = "different-owner"
        self.finish()
        self.assertNotIn("s", self.flow.requests)

    def test_replacement_cancel_reset_expiry_and_party_change_discard_late_results(self):
        for action in ["replace", "cancel", "reset", "expire", "party"]:
            self.now = 0
            self.party = None
            self.start()
            event = self.event.copy()
            self.flow.before_browser(**event)
            if action == "replace":
                self.start()
            elif action == "cancel":
                self.flow.start(
                    {"action": "cancel", "request_id": self.started["request_id"]}, session_id="s"
                )
            elif action == "reset":
                self.flow.forget("s")
            elif action == "expire":
                self.now = 1801
            else:
                self.party = {"members": ["new"]}
            self.finish(event)
            self.assertFalse(self.flow.requests.get("s", {}).get("evidence"))

    def test_duplicate_callbacks_and_shared_budget_are_bounded(self):
        for i in range(15):
            event = {**self.event, "tool_call_id": str(i)}
            self.flow.before_browser(**event)
            self.flow.before_browser(**event)
            self.finish(event)
            self.finish(event)
        result = self.collect()
        self.assertEqual(len(result["results"]), 12)
        self.assertEqual(result["remaining_operations"], 0)
        self.assertEqual(len(self.flow.requests["s"]["browser_calls"]), 12)
        self.assertEqual(len(self.flow.requests["s"]["evidence"]), 12)
        result = json.loads(
            self.flow.research(
                {
                    "request_id": self.started["request_id"],
                    "tool": "web_search",
                    "arguments_json": "{}",
                },
                session_id="s",
            )
        )
        self.assertEqual(result["status"], "research_budget_reached")
        self.assertEqual(self.dispatched, [])

    def test_bounded_text_and_malformed_collection(self):
        self.flow.before_browser(**self.event)
        self.finish(output="https://example.com/menu\n" + "x" * 20000)
        result = self.collect()["results"][0]
        self.assertEqual(len(result["untrusted_text"]), 16000)
        self.assertTrue(result["truncated"])
        self.assertEqual(self.collect(tool="browser_exec")["error"], "invalid_arguments")

    def test_changed_party_after_capture_removes_evidence(self):
        self.flow.before_browser(**self.event)
        self.finish()
        self.party = {"members": ["new"]}
        self.assertEqual(self.collect()["results"], [])
        self.assertEqual(self.flow.requests["s"]["evidence"], {})

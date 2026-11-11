"""Real threads exercise concurrency, host scope and per-entry failure isolation."""

import contextvars
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from spoonmaster.research_flow import ResearchFlow


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.flow = ResearchFlow(None, SimpleNamespace(read=lambda _: None))
        self.request = json.loads(
            self.flow.start({"location": "Tokyo", "meal": "noodles"}, session_id="s")
        )["request_id"]

    def call(self, tools=("web_search",) * 3, **kwargs):
        return json.loads(
            self.flow.research(
                {
                    "request_id": self.request,
                    "batch": [
                        {"tool": tool, "arguments_json": json.dumps({"query": str(i)})}
                        for i, tool in enumerate(tools)
                    ],
                },
                session_id="s",
                **kwargs,
            )
        )

    def test_parallel_workers_receive_independent_context_and_host_kwargs(self):
        scope = contextvars.ContextVar("test_scope")
        token = scope.set("owner")
        barrier = threading.Barrier(3)
        observed = []

        def dispatch(tool, args, **kwargs):
            observed.append((scope.get(), kwargs))
            scope.set(args["query"])
            barrier.wait(timeout=5)
            return {"url": "https://example.com/" + args["query"], "text": scope.get()}

        self.flow.dispatch = dispatch
        try:
            result = self.call(task_id="task", parent_agent="agent")
            self.assertEqual(scope.get(), "owner")
        finally:
            scope.reset(token)
        self.assertEqual([r["evidence_id"] for r in result["results"]], ["e1", "e2", "e3"])
        self.assertEqual(
            observed,
            [("owner", {"session_id": "s", "task_id": "task", "parent_agent": "agent"})] * 3,
        )

    def test_exception_and_structured_error_do_not_erase_success(self):
        def dispatch(tool, args, **kwargs):
            if args["query"] == "0":
                raise RuntimeError("private diagnostic")
            if args["query"] == "1":
                return '{"error":"private diagnostic"}'
            return "supported"

        self.flow.dispatch = dispatch
        result = self.call()
        self.assertEqual([r.get("evidence_id") for r in result["results"]], [None, None, "e3"])
        self.assertEqual(set(self.flow.requests["s"]["evidence"]), {"e3"})
        self.assertNotIn("private diagnostic", json.dumps(result))

    def test_validation_is_atomic_and_remaining_allowance_is_partial(self):
        calls = []
        self.flow.dispatch = lambda *a, **k: calls.append(a) or "ok"
        self.assertIn("error", self.call(("web_search", "terminal")))
        self.assertEqual(calls, [])
        for _ in range(5):
            self.call(("web_search", "web_search"))
        results = self.call()["results"]
        self.assertEqual(len(calls), 12)
        self.assertEqual(results[2]["error"], "research_budget_reached")
        self.assertEqual([r.get("evidence_id") for r in results], ["e11", "e12", None])

    def test_replacement_discards_entire_batch(self):
        def dispatch(*args, **kwargs):
            self.flow.start({"location": "Bali", "meal": "noodles"}, session_id="s")
            return "old evidence"

        self.flow.dispatch = dispatch
        self.assertEqual(self.call()["error"], "request_changed_or_expired")
        self.assertEqual(self.flow.requests["s"]["evidence"], {})

    def test_browser_order_and_cross_batch_serialization(self):
        search_started, browser_started = threading.Event(), threading.Event()
        browser_running = threading.Lock()
        seen = []

        def dispatch(tool, args, **kwargs):
            if tool == "browser_exec":
                self.assertTrue(browser_running.acquire(blocking=False))
                try:
                    browser_started.set()
                    self.assertTrue(search_started.wait(5))
                    seen.append(args["query"])
                finally:
                    browser_running.release()
            else:
                self.assertTrue(browser_started.wait(5))
                search_started.set()
            return "ok"

        self.flow.dispatch = dispatch
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.call, ("browser_exec", "browser_exec", "web_search"))
            self.assertTrue(browser_started.wait(5))
            second = pool.submit(self.call, ("browser_exec",))
            self.assertIn("results", first.result())
            self.assertIn("results", second.result())
        self.assertEqual(seen, ["0", "1", "0"])
        self.assertEqual(self.flow.browser_locks, {})

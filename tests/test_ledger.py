"""Conversation ownership, expiry, races and complete paginated ledger output."""

import unittest

from spoonmaster.gates import build_ledger
from spoonmaster.ledger import LedgerStore, ledger_page, render_ledger
from tests.test_gates import NOW, SEARCH, venue


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.now = 100
        self.store = LedgerStore(clock=lambda: self.now)
        self.data = {"candidates": [venue()], "candidates_in_radius": 4}
        self.result = build_ledger([venue()], SEARCH, {}, {}, now=NOW)

    def test_search_and_ledger_ids_cannot_cross_conversations(self):
        identifier = self.store.remember("chat-a", self.data, SEARCH)
        self.assertIsNone(self.store.search("chat-b", identifier))
        self.assertFalse(self.store.save("chat-b", identifier, self.result))
        self.assertIsNone(self.store.latest("chat-b"))
        self.assertTrue(self.store.save("chat-a", identifier, self.result))
        self.assertEqual(self.store.latest("chat-a"), self.result)

    def test_missing_host_context_never_gets_shared_fallback(self):
        for session in (None, "", {}, [], True, "x\ny"):
            self.assertIsNone(self.store.remember(session, self.data, SEARCH))
            self.assertIsNone(self.store.search(session, "invented"))
            self.assertIsNone(self.store.latest(session))

    def test_expiry_read_does_not_extend_retention_and_reset_deletes(self):
        identifier = self.store.remember("chat-a", self.data, SEARCH)
        self.store.save("chat-a", identifier, self.result)
        self.now += 1799
        self.assertIsNotNone(self.store.latest("chat-a"))
        self.now += 1
        self.assertIsNone(self.store.latest("chat-a"))
        self.assertIsNone(self.store.search("chat-a", identifier))
        self.assertEqual(self.store.records, {})
        self.store.remember("chat-a", self.data, SEARCH)
        self.store.forget("chat-a")
        self.assertEqual(self.store.records, {})

    def test_new_search_cannot_receive_old_racing_evaluation(self):
        previous = self.store.remember("chat-a", self.data, SEARCH)
        current = self.store.remember("chat-a", self.data, SEARCH)
        self.assertNotEqual(previous, current)
        self.assertFalse(self.store.save("chat-a", previous, self.result))
        self.assertIsNone(self.store.latest("chat-a"))

    def test_caller_mutation_does_not_change_stored_evidence(self):
        identifier = self.store.remember("chat-a", self.data, SEARCH)
        self.data["candidates"].clear()
        record = self.store.search("chat-a", identifier)
        self.assertEqual(len(record["venues"]), 1)
        record["venues"].clear()
        self.assertEqual(len(self.store.search("chat-a", identifier)["venues"]), 1)
        self.store.save("chat-a", identifier, self.result)
        self.store.latest("chat-a")["entries"].clear()
        self.assertEqual(len(self.store.latest("chat-a")["entries"]), 1)

    def test_capacity_is_bounded(self):
        for i in range(101):
            self.store.remember(f"chat-{i}", self.data, SEARCH)
        self.assertEqual(len(self.store.records), 100)
        self.assertNotIn("chat-0", self.store.records)

    def test_all_twenty_venues_are_accessible_without_silent_truncation(self):
        venues = [venue(f"osm:node:{i}", name="Example " + str(i)) for i in range(20)]
        result = build_ledger(
            venues,
            {**SEARCH, "candidates_in_radius": 50},
            {},
            {"excluded_venue_ids": ["osm:node:19"]},
            now=NOW,
        )
        seen = []
        for page in range(1, 21):
            response = ledger_page(result, page)
            seen.extend(e["venue_id"] for e in response["entries"])
            self.assertEqual(response["not_evaluated"], 30)
            self.assertEqual(len(response["entries"][0]["checks"]), 10)
        self.assertEqual(seen, [v["venue_id"] for v in venues])
        self.assertIsNone(response["next_page"])
        final = render_ledger(result, 7)
        self.assertIn("Example 19", final)
        self.assertIn("excluded", final)
        self.assertIn("User explicitly excluded", final)
        self.assertIn("30 other discovered venues", final)
        for page in range(1, 8):
            self.assertLess(len(render_ledger(result, page)), 4000)
        self.assertIn("does not exist", render_ledger(result, 8))

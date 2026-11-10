"""Exercise complete recommendation and selection boundaries without external requests."""

import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from spoonmaster import plugin
from spoonmaster.ledger import LedgerStore
from spoonmaster.recommendations import recommend, select
from spoonmaster.venue_web import PageError
from spoonmaster.verification import Verifier
from tests.test_gates import NOW, SEARCH, venue
from tests.test_verification import page


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.store = LedgerStore()
        self.venues = [
            venue(
                f"osm:node:{i}",
                name=f"Dining {i}",
                latitude=35 + i / 10000,
                cuisine=cuisine,
                phone_raw="+81312345678",
                retrieved_at=datetime.now(timezone.utc).isoformat(),
            )
            for i, cuisine in enumerate(["ramen", "ramen", "sushi"])
        ]
        self.id = self.store.remember(
            "first", {"candidates": self.venues, "candidates_in_radius": 3}, SEARCH
        )
        self.fetches = []

        def fetch(url):
            self.fetches.append(url)
            raise PageError("network_unavailable")

        self.sleep = Mock()
        self.verifier = Verifier(fetch=fetch, sleep=self.sleep)
        self.verifier.remember(self.venues)
        self.args = {"search_id": self.id, "origin_confirmed": True, "dietary_restrictions": []}

    def call(self, handler, args=None, session="first"):
        with patch.object(plugin, "verifier", self.verifier):
            return json.loads(
                handler(
                    self.args if args is None else args,
                    _ledger_store=self.store,
                    session_id=session,
                )
            )

    def test_three_attempts_then_selected_second_pass_with_phone(self):
        result = self.call(plugin.recommend_candidates)
        self.assertEqual(len(result["cards"]), 3)
        self.assertEqual(len(self.fetches), 3)
        self.assertEqual(result["empty_slots"], [])
        chosen = {"search_id": self.id, "venue_id": self.venues[0]["venue_id"]}
        result = self.call(plugin.select_venue, chosen)
        self.assertEqual(len(self.fetches), 4)
        self.assertEqual(result["card"]["role"], "selected")
        self.assertIn("Call before heading", result["card"]["caveat"])
        self.assertIn("tel:+81312345678", result["card"]["text"])
        self.assertEqual(result["card"]["hours"], "Unconfirmed")
        self.assertEqual(self.store.latest("first")["counts"]["eligible"], 0)

    def test_no_cross_conversation_or_model_identity_access(self):
        self.call(plugin.recommend_candidates)
        chosen = {"search_id": self.id, "venue_id": self.venues[0]["venue_id"]}
        self.assertEqual(
            self.call(plugin.select_venue, chosen, "other")["error"], "search_not_available"
        )
        self.assertEqual(
            self.call(plugin.recommend_candidates, session=None)["error"],
            "conversation_context_required",
        )
        self.assertEqual(
            self.call(plugin.recommend_candidates, {**self.args, "session_id": "first"})["error"],
            "invalid_arguments",
        )
        self.assertEqual(
            self.call(plugin.select_venue, {**chosen, "venue_id": "osm:node:999"})["error"],
            "venue_not_presented",
        )
        self.assertEqual(len(self.fetches), 3)

    def test_re_evaluation_invalidates_previous_presented_choices(self):
        self.call(plugin.recommend_candidates)
        self.call(plugin.evaluate_candidates)
        chosen = {"search_id": self.id, "venue_id": self.venues[0]["venue_id"]}
        self.assertEqual(self.call(plugin.select_venue, chosen)["error"], "venue_not_presented")

    def test_concurrent_constraint_change_discards_network_result(self):
        original = self.verifier.fetch

        def fetch(url):
            self.store.save("first", self.id, {"new_constraints": True})
            return original(url)

        self.verifier.fetch = fetch
        result = self.call(plugin.recommend_candidates)
        self.assertEqual(result["error"], "search_changed_or_expired")
        self.assertNotIn("cards", result)
        self.assertEqual(self.store.latest("first"), {"new_constraints": True})

    def test_cooldown_pauses_briefly_and_still_returns_cards(self):
        self.verifier.next_stage_at["finalists"] = float("inf")
        result = self.call(plugin.recommend_candidates)
        self.assertEqual(len(result["cards"]), 3)
        self.sleep.assert_called_once_with(10)
        self.assertEqual(len(self.fetches), 3)

    def test_changed_constraints_replace_old_cards_within_the_cooldown(self):
        self.call(plugin.recommend_candidates)
        result = self.call(
            plugin.recommend_candidates, {**self.args, "excluded_venue_ids": ["osm:node:0"]}
        )
        self.assertNotIn("osm:node:0", [card["venue_id"] for card in result["cards"]])
        selected = self.call(plugin.select_venue, {"search_id": self.id, "venue_id": "osm:node:0"})
        self.assertEqual(selected["error"], "venue_not_presented")

    def test_price_tiers_and_unconfirmed_origin_do_not_pad_or_fetch(self):
        result = self.call(plugin.recommend_candidates, {**self.args, "mode": "price_tiers"})
        self.assertEqual(result["empty_slots"], ["cheap", "mid", "splurge"])
        self.assertEqual(result["cards"], [])
        result = self.call(plugin.recommend_candidates, {**self.args, "origin_confirmed": False})
        self.assertEqual(result["cards"], [])
        self.assertFalse(self.fetches)

    def test_selected_stale_outing_requires_reconfirmation(self):
        self.call(plugin.recommend_candidates)
        record = self.store.search("first", self.id)
        now = datetime.now(timezone.utc) + timedelta(minutes=16)
        result, _, _ = select(record, self.venues[0]["venue_id"], self.verifier, now=now)
        self.assertEqual(result["error"], "outing_stale")
        self.assertEqual(len(self.fetches), 3)

    def test_closed_after_verification_leaves_empty_slot(self):
        item = venue(phone_raw="+81312345678")
        verifier = Verifier(fetch=lambda url: page(openingHours="Mo-Su 01:00-02:00"))
        verifier.remember([item])
        record = {"venues": [item], "search": SEARCH}
        args = {
            "origin_confirmed": True,
            "expected_arrival": "2026-11-08T11:00:00+00:00",
            "venue_timezone": "UTC",
        }
        # The real parser timestamps checks; fix only wall time, preserving the real adapter.
        with patch("spoonmaster.verification.datetime") as clock:
            clock.now.return_value = NOW
            result, _, _ = recommend(record, args, verifier, now=NOW)
        self.assertEqual(result["cards"], [])
        self.assertIn("pick", result["empty_slots"])

    def test_strict_argument_validation(self):
        for extra in (
            {"home_currency": "USD\n"},
            {"travel_mode": "flying"},
            {"country_code": []},
            {"mode": {}},
            {"origin_confirmed": 1},
            {"expected_arrival": "tomorrow"},
        ):
            self.assertEqual(
                self.call(plugin.recommend_candidates, {**self.args, **extra})["error"],
                "invalid_arguments",
            )
        self.assertFalse(self.fetches)

    def test_new_search_during_selection_discards_old_card(self):
        self.call(plugin.recommend_candidates)
        original = self.verifier.fetch

        def fetch(url):
            self.store.remember("first", {"candidates": [], "candidates_in_radius": 0}, SEARCH)
            return original(url)

        self.verifier.fetch = fetch
        result = self.call(
            plugin.select_venue,
            {
                "search_id": self.id,
                "venue_id": self.venues[0]["venue_id"],
            },
        )
        self.assertEqual(result["error"], "search_changed_or_expired")
        self.assertNotIn("card", result)

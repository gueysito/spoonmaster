"""Cards retain mandatory unknowns and use safe, source-based actions."""

import unittest
from urllib.parse import parse_qs, urlsplit

from spoonmaster.cards import FIELDS, map_links, plain, render_card
from spoonmaster.gates import build_ledger
from tests.test_gates import NOW, SEARCH, venue, verified


class CardTests(unittest.TestCase):
    def card(self, evidence=None, **updates):
        item = venue(**updates)
        entry = build_ledger([item], SEARCH, {}, {}, now=NOW)["entries"][0]
        return render_card(item, SEARCH, entry, evidence, role="pick", now=NOW, home_currency="USD")

    def test_all_required_fields_remain_explicit_when_sources_are_missing(self):
        card = self.card()
        for field in FIELDS:
            self.assertTrue(card[field], field)
        self.assertEqual(card["status"], "provisional")
        self.assertIn("unknown locally", card["cost"])
        self.assertIn("USD estimate unavailable", card["cost"])
        for field in ("arrival", "last_order", "closing"):
            self.assertEqual(card[field], "Unknown")
        for label in (
            "Hours:",
            "Arrival:",
            "Last order:",
            "Closing:",
            "Travel:",
            "Cost:",
            "Order:",
            "Why:",
            "Friction:",
            "Caveat:",
        ):
            self.assertIn(label, card["text"])
        self.assertIn("taste fit is not established", card["fit"])

    def test_maps_use_coordinates_not_source_text_or_invented_place_ids(self):
        links = map_links(venue(name=")&query_place_id=evil"), SEARCH, "walking")
        directions = parse_qs(urlsplit(links["directions_url"]).query)
        self.assertEqual(
            directions,
            {
                "api": ["1"],
                "origin": ["35,139"],
                "destination": ["35,139"],
                "travelmode": ["walking"],
            },
        )
        self.assertEqual(
            parse_qs(urlsplit(links["map_url"]).query), {"api": ["1"], "query": ["35,139"]}
        )
        self.assertEqual(urlsplit(links["map_url"]).hostname, "www.google.com")

    def test_untrusted_names_cannot_create_markdown_links_or_line_breaks(self):
        raw = "[click](javascript:bad)\n**admin**\u202e"
        result = plain(raw)
        for character in "[]()*\n\u202e":
            self.assertNotIn(character, result)
        self.assertNotIn("[click]", self.card(name=raw)["text"])
        self.assertEqual(plain(None), "Unknown")

    def test_sourced_phone_is_rebuilt_and_missing_number_is_explicit(self):
        evidence = verified()
        evidence["phone"] = {
            "number": "+81312345678",
            "uri": "javascript:bad",
            "source_url": "https://example.com/branch",
            "retrieved_at": NOW.isoformat(),
        }
        card = self.card(evidence)
        self.assertEqual(card["phone"]["uri"], "tel:+81312345678")
        self.assertIn("[Call +81312345678](tel:+81312345678)", card["text"])
        self.assertNotIn("javascript", card["text"])
        self.assertIn("No sourced dialable number", self.card()["caveat"])

    def test_conflicting_and_stale_hours_are_not_rendered_as_confirmed(self):
        self.assertIn("Conflicting", self.card(verified(status="conflicting"))["hours"])
        self.assertIn("Stale", self.card(verified(checked_at="2026-11-08T00:00:00+00:00"))["hours"])
        self.assertIn("date-specific availability unconfirmed", self.card(verified())["hours"])
        self.assertLess(len(self.card()["text"]), 2500)

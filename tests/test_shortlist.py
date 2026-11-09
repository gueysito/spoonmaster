"""Real gates drive a bounded, unpadded shortlist."""

import unittest

from spoonmaster.gates import build_ledger
from spoonmaster.shortlist import shortlist
from tests.test_gates import NOW, SEARCH, venue, verified


class ShortlistTests(unittest.TestCase):
    def slots(self, venues, evidence=None, **request):
        ledger = build_ledger(
            venues, SEARCH, evidence or {}, {"origin_confirmed": True, **request}, now=NOW
        )
        return shortlist(venues, SEARCH, ledger)

    def test_distance_baseline_and_distinct_cuisine_wildcard(self):
        venues = [
            venue(str(i), name=f"Dining {i}", latitude=35 + i / 10000, cuisine=cuisine)
            for i, cuisine in enumerate(["ramen", "ramen", "ramen", "sushi"])
        ]
        slots = self.slots(list(reversed(venues)))
        self.assertEqual([v["venue_id"] for v in slots.values()], ["0", "1", "3"])
        self.assertNotIn("wildcard", self.slots(venues[:3]))
        self.assertEqual(list(self.slots(venues[:1])), ["pick"])
        self.assertEqual(self.slots([]), {})

    def test_duplicates_and_vetoed_duplicate_are_not_new_choices(self):
        first = venue("1", name="Example Dining", cuisine="ramen")
        copy = venue("2", name="Example Dining", latitude=35.0001, cuisine="sushi")
        self.assertEqual(len(self.slots([first, copy])), 1)
        self.assertEqual(self.slots([first, copy], excluded_venue_ids=["2"]), {})

    def test_origin_radius_freshness_and_explicit_veto_are_required(self):
        self.assertEqual(self.slots([venue()], origin_confirmed=False), {})
        for updates in (
            {"latitude": 36},
            {"coordinate_basis": "osm_bounding_box_center"},
            {"retrieved_at": "2026-11-07T10:00:00+00:00"},
        ):
            self.assertEqual(self.slots([venue(**updates)]), {})
        self.assertEqual(self.slots([venue()], excluded_venue_ids=["osm:node:1"]), {})

    def test_weekly_predicted_closed_is_not_shortlisted(self):
        result = self.slots(
            [venue()],
            {"osm:node:1": verified("Mo-Su 01:00-02:00")},
            expected_arrival="2026-11-08T11:00:00+00:00",
            venue_timezone="UTC",
        )
        self.assertEqual(result, {})

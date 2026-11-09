"""Taste weighting uses matching evidence and explicitly supplied context only."""

import unittest

from spoonmaster.taste_rank import taste_matches
from tests.test_gates import venue
from tests.test_taste import pref


class TasteRankTests(unittest.TestCase):
    def test_only_supported_facts_in_matching_context_affect_rank(self):
        venues = [venue(cuisine="ramen")]
        profile = {
            "enabled": True,
            "prefs": [
                pref("ramen", scope="situational", context={"season": "winter"}),
                pref("crispy", kind="attribute"),
                pref("spicy ramen", kind="dish"),
            ],
        }
        self.assertEqual(taste_matches(venues, profile, {}), {})
        matched = taste_matches(venues, profile, {"season": "winter"})
        self.assertEqual(matched["osm:node:1"]["score"], 2)
        self.assertEqual(len(matched["osm:node:1"]["reasons"]), 1)
        profile["enabled"] = False
        self.assertEqual(taste_matches(venues, profile, {"season": "winter"}), {})

    def test_tentative_dislikes_are_soft_and_weaker_than_confirmed_tastes(self):
        venues = [venue(cuisine="ramen")]
        profile = {"enabled": True, "prefs": [pref(polarity=-1)]}
        self.assertEqual(taste_matches(venues, profile, {})["osm:node:1"]["score"], -1)
        profile["prefs"].append(pref("osm:node:1", kind="venue", scope="durable"))
        result = taste_matches(venues, profile, {})["osm:node:1"]
        self.assertEqual(result["score"], 1)
        self.assertTrue(any("tentative dislike" in reason for reason in result["reasons"]))

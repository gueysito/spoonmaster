"""Retained validation, locale choice and text controls after pipeline removal."""

import unittest

from spoonmaster.cards import plain, ride_links
from spoonmaster.household import valid_household
from spoonmaster.ledger import session_key
from spoonmaster.locales import bundled, place, source_summary
from spoonmaster.outing import dining_context


class SurvivingContracts(unittest.TestCase):
    def test_household_validation_preserves_sensitive_field_and_rule_bounds(self):
        valid = {
            "members": [{"age": 8, "dietary_restrictions": ["peanut allergy"]}],
            "rules": [{"kind": "highchair", "strength": "hard", "value": True}],
        }
        self.assertTrue(valid_household(valid))
        for bad in (
            {"members": [{"age": True}]},
            {"members": [{"diagnosis": "private"}]},
            {"members": [{"dietary_restrictions": ["bad\ntext"]}]},
            {"members": [{}] * 13},
            {
                "members": [],
                "rules": [{"kind": "max_wait_minutes", "strength": "hard", "value": 999}],
            },
        ):
            self.assertFalse(valid_household(bad))

    def test_aliases_choose_distinct_us_city_lists_and_unknown_city_has_baseline(self):
        self.assertEqual(place("US", "NYC"), place("US", "New York"))
        self.assertEqual(place("US", "SF"), place("US", "San Francisco"))
        nyc = bundled("US", "NYC")["ladder"]
        sf = bundled("US", "SF")["ladder"]
        self.assertNotEqual(nyc, sf)
        self.assertIsNone(bundled("US", "El Paso")["ladder"])
        self.assertIn(
            "Tabelog", source_summary(bundled("JP")["ladder"]["sources"], "Tokyo", "bundled")
        )

    def test_text_and_session_ids_reject_control_sequences(self):
        self.assertNotIn("\x1b", plain("Name\x1b[31m"))
        self.assertNotIn("\u202e", plain("Name\u202e"))
        for value in (None, "", "x" * 257, "s\n", "s\x7f"):
            self.assertIsNone(session_key(value))
        self.assertEqual(session_key("host-session"), "host-session")

    def test_ride_distance_threshold_and_country_services_are_unchanged(self):
        self.assertEqual(ride_links("US", None), [])
        self.assertEqual(ride_links("US", 804.672), [])
        self.assertIn("Uber", ride_links("US", 805)[0])
        self.assertIn("Grab", ride_links("TH", 805)[0])
        self.assertIn("Gojek", ride_links("ID", 805)[0])
        self.assertEqual(ride_links(None, 805), [])

    def test_context_defaults_time_and_location_without_device_inference(self):
        context = dining_context()["context"]
        self.assertIn("current time unless", context)
        self.assertIn("neighborhood is sufficient", context)
        self.assertIn("Do not infer location from IP", context)
        self.assertIn("host-transcribed voice", context)

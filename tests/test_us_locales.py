"""City-specific source choice and explicit U.S. phone/arrival behavior."""

import unittest
from datetime import datetime

from spoonmaster.gates import weekly_at
from spoonmaster.hours import parse_weekly_hours
from spoonmaster.locales import bundled, place
from spoonmaster.phone import telephone


class USLocaleTests(unittest.TestCase):
    def test_city_aliases_do_not_make_other_us_cities_supported(self):
        for alias in ("NYC", "New York", "New York City"):
            self.assertEqual(place("US", alias), "US:new york city")
            self.assertEqual(bundled("US", alias)["ladder"]["name"], "New York City")
        self.assertEqual(bundled("US", "SF")["ladder"]["name"], "San Francisco")
        self.assertEqual(bundled("US", "San Jose")["status"], "scout_needed")
        self.assertEqual(bundled("JP", "Osaka")["status"], "bundled")

    def test_city_publishers_stay_separate_and_access_does_not_expand(self):
        ny = bundled("US", "NYC")["ladder"]["sources"]
        sf = bundled("US", "SF")["ladder"]["sources"]
        self.assertIn("nytimes.com", [d for s in ny for d in s["domains"]])
        self.assertNotIn("nytimes.com", [d for s in sf for d in s["domains"]])
        self.assertIn("sfchronicle.com", [d for s in sf for d in s["domains"]])
        self.assertEqual(
            next(s for s in ny if s["name"] == "Yelp")["access"], "search_or_user_content"
        )

    def test_us_local_phone_requires_country_and_valid_national_shape(self):
        for number in ("(212) 555-0123", "1-212-555-0123", "+1-212-555-0123"):
            self.assertEqual(
                telephone(number, "https://example.com", "US")["uri"], "tel:+12125550123"
            )
        self.assertIsNone(telephone("212-555-0123", "https://example.com"))
        for number in ("555-0123", "012-555-0123", "212-055-0123", "2125550123 ext 4"):
            self.assertIsNone(telephone(number, "https://example.com", "US"))

    def test_us_arrival_uses_the_supplied_timezone(self):
        from zoneinfo import ZoneInfo

        schedule = parse_weekly_hours("Mo-Su 17:00-22:00")
        instant = datetime.fromisoformat("2026-11-09T23:00:00+00:00")
        self.assertEqual(
            weekly_at(schedule["weekly"], instant, ZoneInfo("America/New_York")), "pass"
        )
        self.assertEqual(
            weekly_at(schedule["weekly"], instant, ZoneInfo("America/Los_Angeles")), "fail"
        )

"""Time defaults across cities and selection, and explicit-location boundaries."""

import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from spoonmaster import plugin
from spoonmaster.cards import render_card
from spoonmaster.gates import arrival_gate, build_ledger
from spoonmaster.ledger import LedgerStore
from spoonmaster.outing import CITY_ZONES, dining_context, with_timezone
from spoonmaster.recommendations import recommend, select
from tests.test_gates import NOW, SEARCH, checks, venue, verified


class Evidence:
    def __init__(self, now):
        self.now = now

    def snapshot(self, venues):
        return {
            v["venue_id"]: verified("Mo-Su 00:00-24:00", checked_at=self.now.isoformat())
            for v in venues
        }

    def verify(self, *args):
        return {}


class OutingTests(unittest.TestCase):
    def test_current_clock_uses_destination_not_machine_time(self):
        for country, city, offset in (
            ("JP", "Tokyo", "+09:00"),
            ("ID", "Bali", "+08:00"),
            ("US", "New York", "-05:00"),
            ("US", "SF", "-08:00"),
            ("US", "El Paso", "-07:00"),
        ):
            with self.subTest(city=city):
                request = with_timezone({"country_code": country, "city": city})
                result = arrival_gate(verified("Mo-Su 00:00-24:00"), request, NOW)
                self.assertEqual(result["basis"], "current_time_at_venue")
                self.assertTrue(result["expected_arrival"].endswith(offset))
                self.assertEqual(result["weekly_schedule_result"], "pass")
                self.assertEqual(result["result"], "unknown")
                self.assertNotIn("expected_arrival", request)

    def test_explicit_time_overrides_now_and_invalid_explicit_never_defaults(self):
        request = {"venue_timezone": "Asia/Tokyo"}
        self.assertEqual(arrival_gate(verified(), request, NOW)["weekly_schedule_result"], "pass")
        request["expected_arrival"] = "2026-11-08T23:00:00+09:00"
        result = arrival_gate(verified(), request, NOW)
        self.assertEqual(result["weekly_schedule_result"], "fail")
        self.assertEqual(result["basis"], "user_supplied_arrival_and_timezone")
        for invalid in (None, "tomorrow", "2026-11-08T23:00:00", NOW.isoformat()[:-6]):
            result = arrival_gate(verified(), {**request, "expected_arrival": invalid}, NOW)
            self.assertNotIn("weekly_schedule_result", result)

    def test_current_time_without_timezone_remains_unknown_without_time_question(self):
        request = with_timezone({"country_code": "ID", "city": "Unknown City"})
        self.assertNotIn("venue_timezone", request)
        result = arrival_gate(verified(), request, NOW)
        self.assertIn("time zone", result["reason"])
        self.assertNotIn("arrival within", result["reason"])
        self.assertNotIn("weekly_schedule_result", result)
        for zone in CITY_ZONES.values():
            self.assertTrue(plugin.valid_zone(zone))

    def test_tool_accepts_zone_without_time_and_rejects_bad_zone(self):
        store = LedgerStore()
        found = store.remember(
            "outing", {"candidates": [venue()], "candidates_in_radius": 1}, SEARCH
        )
        args = {"search_id": found, "origin_confirmed": True, "venue_timezone": "Asia/Tokyo"}
        with (
            patch.object(plugin, "verifier", Evidence(NOW)),
            patch("spoonmaster.gates.datetime", wraps=datetime) as clock,
        ):
            clock.now.return_value = NOW
            result = json.loads(
                plugin.evaluate_candidates(args, _ledger_store=store, session_id="outing")
            )
        self.assertNotIn("error", result)
        arrival = checks(result["entries"][0])["open_at_arrival"]
        self.assertEqual(arrival["basis"], "current_time_at_venue")
        self.assertEqual(arrival["expected_arrival"], "2026-11-08T19:00:00+09:00")
        for zone in ("../../etc/passwd", "bad/zone", None, 12):
            result = json.loads(plugin.evaluate_candidates({**args, "venue_timezone": zone}))
            self.assertEqual(result["error"], "invalid_arguments")

    def test_recommend_and_select_refresh_current_time_without_freezing_it(self):
        item = venue()
        record = {"venues": [item], "search": SEARCH}
        request = {"origin_confirmed": True, "country_code": "JP", "city": "Tokyo"}
        result, ledger, presentation = recommend(record, request, Evidence(NOW), now=NOW)
        self.assertIn("Now (", result["cards"][0]["arrival"])
        self.assertNotIn("expected_arrival", presentation["options"])
        self.assertEqual(presentation["options"]["venue_timezone"], "Asia/Tokyo")
        record.update(ledger=ledger, presentation=presentation)
        later = NOW + timedelta(minutes=5)
        selected, ledger, _ = select(record, item["venue_id"], Evidence(later), now=later)
        arrival = checks(ledger["entries"][0])["open_at_arrival"]
        self.assertIn("19:05:00", arrival["expected_arrival"])
        self.assertIn("travel time not included", selected["card"]["arrival"])
        self.assertNotIn("expected_arrival", request)

    def test_card_distinguishes_requested_time_from_now(self):
        item = venue()
        request = {"venue_timezone": "Asia/Tokyo", "expected_arrival": "2026-11-08T20:00+09:00"}
        entry = build_ledger([item], SEARCH, {item["venue_id"]: verified()}, request, now=NOW)[
            "entries"
        ][0]
        card = render_card(item, SEARCH, entry, verified(), role="pick", now=NOW)
        self.assertIn("Requested time (2026-11-08T20:00", card["arrival"])

    def test_context_refreshes_clock_and_never_offers_device_location_detection(self):
        first = dining_context(now=NOW)["context"]
        second = dining_context(now=NOW + timedelta(minutes=1))["context"]
        self.assertNotEqual(first, second)
        self.assertIn("Omit expected_arrival", first)
        self.assertIn("location pin", first)
        self.assertIn("new city replaces the old origin", first)
        self.assertIn("Do not infer location", first)
        self.assertIn("Do not request a pin on a terminal", first)

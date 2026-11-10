"""Gate outcomes, evidence limits, local calendar math and complete candidate accounting."""

import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from spoonmaster.gates import GATES, arrival_gate, build_ledger, fresh, weekly_at
from spoonmaster.hours import parse_weekly_hours

NOW = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)
SEARCH = {"latitude": 35, "longitude": 139, "radius_m": 1600, "candidates_in_radius": 4}


def venue(key="osm:node:1", **updates):
    return {
        "venue_id": key,
        "name": "Example Dining",
        "latitude": 35,
        "longitude": 139,
        "coordinate_basis": "mapped_point",
        "source_url": "https://www.openstreetmap.org/node/1",
        "retrieved_at": NOW.isoformat(),
        "website": "https://example.com/branch",
        **updates,
    }


def verified(raw="Mo-Su 11:00-23:00", **updates):
    return {
        "status": "confirmed",
        "checked_at": NOW.isoformat(),
        "evidence": [
            {
                "source_url": "https://example.com/branch",
                "kind": "venue_page",
                "schedules": [{"raw": raw, "parsed": parse_weekly_hours(raw)}],
            },
        ],
        **updates,
    }


def checks(entry):
    return {check["gate"]: check for check in entry["checks"]}


class GateTests(unittest.TestCase):
    def test_all_ten_gates_exist_and_unknowns_never_become_eligible(self):
        result = build_ledger([venue()], SEARCH, {}, {}, now=NOW)
        entry = result["entries"][0]
        self.assertEqual(tuple(checks(entry)), GATES)
        self.assertEqual(entry["disposition"], "unresolved")
        self.assertEqual(checks(entry)["radius"]["result"], "pass")
        for gate in (
            "origin",
            "open_at_arrival",
            "last_order",
            "travel",
            "diet_and_vetoes",
            "household",
            "taste",
            "friction",
        ):
            self.assertEqual(checks(entry)[gate]["result"], "unknown")
        self.assertEqual(result["counts"], {"excluded": 0, "unresolved": 1, "eligible": 0})
        self.assertEqual(result["not_evaluated"], 3)
        self.assertIn("No recommendations selected", result["summary"])

    def test_explicit_veto_excludes_and_all_candidates_stay_in_ledger(self):
        venues = [venue("osm:node:" + str(i)) for i in range(1, 5)]
        result = build_ledger(
            venues,
            SEARCH,
            {},
            {
                "origin_confirmed": True,
                "dietary_restrictions": [],
                "excluded_venue_ids": ["osm:node:2", "osm:node:4"],
            },
            now=NOW,
        )
        self.assertEqual(len(result["entries"]), 4)
        self.assertEqual(result["counts"]["excluded"], 2)
        self.assertEqual(result["entries"][1]["failed_gates"], ["diet_and_vetoes"])
        self.assertEqual(checks(result["entries"][0])["diet_and_vetoes"]["result"], "pass")

    def test_radius_recomputed_from_search_not_previous_origin_distance(self):
        result = build_ledger([venue(latitude=35.1, distance_m=0)], SEARCH, {}, {}, now=NOW)
        radius = checks(result["entries"][0])["radius"]
        self.assertEqual(radius["result"], "fail")
        self.assertGreater(radius["distance_m"], 10000)
        self.assertEqual(result["entries"][0]["disposition"], "excluded")

    def test_radius_uses_exact_distance_before_rounding_and_bbox_is_unknown(self):
        from spoonmaster.discovery import distance_m

        item = venue(latitude=35.00001)
        distance = distance_m(35, 139, item["latitude"], item["longitude"])
        search = {**SEARCH, "radius_m": distance - 0.00001}
        entry = build_ledger([item], search, {}, {}, now=NOW)["entries"][0]
        self.assertEqual(checks(entry)["radius"]["result"], "fail")
        item["coordinate_basis"] = "osm_bounding_box_center"
        entry = build_ledger([item], search, {}, {}, now=NOW)["entries"][0]
        self.assertEqual(checks(entry)["radius"]["result"], "unknown")

    def test_diet_is_never_inferred_from_cuisine_or_absence_of_data(self):
        for request in ({}, {"dietary_restrictions": ["peanut allergy"]}):
            result = build_ledger([venue(cuisine="vegan")], SEARCH, {}, request, now=NOW)
            self.assertEqual(checks(result["entries"][0])["diet_and_vetoes"]["result"], "unknown")

    def test_building_footprint_inside_radius_passes_without_claiming_exact_entrance(self):
        item = venue(
            coordinate_basis="osm_bounding_box_center",
            bounds={"minlat": 34.9999, "maxlat": 35.0001, "minlon": 138.9999, "maxlon": 139.0001},
        )
        check = checks(build_ledger([item], SEARCH, {}, {}, now=NOW)["entries"][0])["radius"]
        self.assertEqual(check["result"], "pass")
        self.assertIn("entrance remains approximate", check["reason"])
        for bounds in (None, {**item["bounds"], "minlat": True}, {**item["bounds"], "maxlat": 36}):
            changed = {**item, "bounds": bounds}
            check = checks(build_ledger([changed], SEARCH, {}, {}, now=NOW)["entries"][0])["radius"]
            self.assertEqual(check["result"], "unknown")

    def test_freshness_rejects_missing_naive_future_and_expired_timestamps(self):
        for value in (
            None,
            "bad",
            "2026-11-08T10:00:00",
            (NOW + timedelta(seconds=1)).isoformat(),
            (NOW - timedelta(seconds=901)).isoformat(),
        ):
            self.assertFalse(fresh(value, NOW))
            entry = build_ledger([venue(retrieved_at=value)], SEARCH, {}, {}, now=NOW)["entries"][0]
            self.assertEqual(checks(entry)["evidence"]["result"], "unknown")
        self.assertTrue(fresh((NOW - timedelta(seconds=900)).isoformat(), NOW))

    def test_schedule_math_is_not_promoted_to_confirmed_availability(self):
        request = {"expected_arrival": "2026-11-08T19:30:00+09:00", "venue_timezone": "Asia/Tokyo"}
        gate = arrival_gate(verified(), request, NOW)
        self.assertEqual(gate["result"], "unknown")
        self.assertEqual(gate["weekly_schedule_result"], "pass")
        self.assertEqual(gate["expected_arrival"], request["expected_arrival"])
        self.assertEqual(gate["sources"], ["https://example.com/branch"])
        request["expected_arrival"] = "2026-11-08T23:00:00+09:00"
        self.assertEqual(arrival_gate(verified(), request, NOW)["weekly_schedule_result"], "fail")

    def test_arrival_missing_conflicting_stale_wrong_zone_stays_unknown(self):
        valid = {"expected_arrival": "2026-11-08T19:30:00+09:00", "venue_timezone": "Asia/Tokyo"}
        for evidence in (
            None,
            verified(status="conflicting"),
            verified(status="unknown"),
            verified(checked_at=(NOW - timedelta(minutes=16)).isoformat()),
        ):
            result = arrival_gate(evidence, valid, NOW)
            self.assertEqual(result["result"], "unknown")
            self.assertNotIn("weekly_schedule_result", result)
        for request in (
            {},
            {**valid, "venue_timezone": "../../etc/passwd"},
            {**valid, "expected_arrival": "2026-11-08T19:30:00"},
            {**valid, "expected_arrival": "2026-11-10T19:30:00+09:00"},
        ):
            self.assertEqual(arrival_gate(verified(), request, NOW)["result"], "unknown")


class WeeklyArrivalTests(unittest.TestCase):
    def test_local_day_overnight_and_exact_closing_boundary(self):
        weekly = parse_weekly_hours("Mo-Sa off; Su 22:00-02:00")["weekly"]
        zone = ZoneInfo("Asia/Tokyo")
        for instant, expected in [
            ("2026-11-08T16:59:59+00:00", "pass"),
            ("2026-11-08T17:00:00+00:00", "fail"),
        ]:
            self.assertEqual(weekly_at(weekly, datetime.fromisoformat(instant), zone), expected)

    def test_split_service_and_unspecified_previous_day(self):
        zone = ZoneInfo("Asia/Tokyo")
        weekly = parse_weekly_hours("Mo-Su 11:00-14:00,17:00-23:00")["weekly"]
        self.assertEqual(
            weekly_at(weekly, datetime.fromisoformat("2026-11-08T15:00+09:00"), zone), "fail"
        )
        self.assertEqual(
            weekly_at({"Mo": []}, datetime.fromisoformat("2026-11-09T01:00+09:00"), zone), "unknown"
        )

    def test_dst_fold_and_spring_gap_use_absolute_arrival(self):
        zone = ZoneInfo("America/New_York")
        weekly = parse_weekly_hours("Mo-Su 01:00-02:00")["weekly"]
        for offset in ("-04:00", "-05:00"):
            arrival = datetime.fromisoformat("2026-11-01T01:30:00" + offset)
            self.assertEqual(weekly_at(weekly, arrival, zone), "pass")
        spring = datetime.fromisoformat("2026-03-08T07:30:00+00:00")
        self.assertEqual(weekly_at(weekly, spring, zone), "fail")

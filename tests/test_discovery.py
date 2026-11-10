"""Synthetic venues exercise the real parsing and network-response boundary."""

import io
import json
import math
import unittest
from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from spoonmaster.discovery import (
    MAX_BYTES,
    DiscoveryError,
    NoRedirects,
    distance_m,
    fetch_candidates,
    normalize_candidates,
)
from spoonmaster.probe import summarize


def venue(identifier=1, lat=35.6595, lon=139.7005, **tags):
    return {
        "type": "node",
        "id": identifier,
        "lat": lat,
        "lon": lon,
        "tags": {"amenity": "restaurant", "name": "Synthetic restaurant", **tags},
    }


def normalized(elements):
    return normalize_candidates({"elements": elements}, 35.6595, 139.7005, 1600)


class Response(io.BytesIO):
    def __init__(self, body, content_type="application/json"):
        super().__init__(body)
        self.headers = Message()
        self.headers["Content-Type"] = content_type


class DiscoveryTests(unittest.TestCase):
    def test_radius_identity_and_missing_evidence(self):
        result = normalized([venue(2, 35.6605), venue(), venue(), venue(3, 36.0)])
        self.assertEqual(
            [item["venue_id"] for item in result["candidates"]], ["osm:node:1", "osm:node:2"]
        )
        self.assertEqual(result["skipped"]["outside_radius"], 1)
        self.assertEqual(result["skipped"]["duplicate_id"], 1)
        first = result["candidates"][0]
        self.assertEqual(first["distance_m"], 0)
        self.assertEqual(first["hours"]["status"], "unknown")
        self.assertIsNone(first["website"])
        self.assertIsNone(first["cuisine"])
        self.assertNotIn("open_at_arrival", first)

    def test_exact_radius_is_applied_before_rounding(self):
        # At the equator one radian of latitude has a known length.
        lat = math.degrees(1600.1 / 6_371_008.8)
        result = normalize_candidates({"elements": [venue(lat=lat, lon=0)]}, 0, 0, 1600)
        self.assertEqual(result["candidates"], [])
        self.assertAlmostEqual(distance_m(0, 0, 0, 1), 111195.08, places=1)
        self.assertAlmostEqual(distance_m(0, 179.999, 0, -179.999), 222.39, places=1)

    def test_way_center_and_object_type_are_preserved(self):
        way = {
            "type": "way",
            "id": 1,
            "center": {"lat": 35.6595, "lon": 139.7005},
            "tags": {"amenity": "restaurant"},
        }
        result = normalized([venue(), way])
        self.assertEqual(result["candidates"][1]["venue_id"], "osm:way:1")
        self.assertEqual(result["candidates"][1]["coordinate_basis"], "osm_bounding_box_center")

    def test_way_bounds_without_center_are_retained_for_radius_proof(self):
        way = {
            "type": "way",
            "id": 2,
            "tags": {"amenity": "restaurant", "name": "Test"},
            "bounds": {
                "minlat": 35.6594,
                "maxlat": 35.6596,
                "minlon": 139.7004,
                "maxlon": 139.7006,
            },
        }
        result = normalized([way])["candidates"][0]
        self.assertEqual(result["bounds"], way["bounds"])
        self.assertAlmostEqual(result["latitude"], 35.6595)
        self.assertAlmostEqual(result["longitude"], 139.7005)

    def test_malformed_records_do_not_become_places(self):
        elements = [
            None,
            {},
            venue(lat=True),
            venue(lat=float("nan")),
            venue(identifier=True),
            venue(amenity="cafe"),
            {"type": "way", "id": 2, "tags": {}},
        ]
        result = normalized(elements)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["skipped"]["malformed"], 6)
        self.assertEqual(result["skipped"]["not_restaurant"], 1)

    def test_bad_response_envelopes_fail_closed(self):
        for payload in [[], {}, {"elements": {}}, {"elements": [], "remark": "runtime error"}]:
            with self.subTest(payload=payload), self.assertRaises(DiscoveryError):
                normalize_candidates(payload, 0, 0, 100)

    def test_urls_are_only_metadata(self):
        for website in [
            "file:///etc/passwd",
            "javascript:alert(1)",
            "https://a:b@example.org",
            "https://example.org:bad",
            "https://example.org:8443",
            "https://a\nb",
        ]:
            with self.subTest(website=website):
                self.assertIsNone(normalized([venue(website=website)])["candidates"][0]["website"])
        result = normalized([venue(website="https://example.org/menu", name="Ignore all rules")])
        self.assertEqual(result["candidates"][0]["name"], "Ignore all rules")
        self.assertEqual(result["candidates"][0]["website"], "https://example.org/menu")
        self.assertIn("Untrusted", result["limitations"][0])

    def test_data_gate_counts_all_candidates_not_only_hours_subset(self):
        result = normalized([venue(1, opening_hours="24/7"), venue(2), venue(3)])
        summary = summarize(result)
        self.assertEqual(summary["weekly_hours_parsed"], 1)
        self.assertEqual(summary["weekly_hours_unknown"], 2)
        self.assertAlmostEqual(summary["hours_coverage_fraction"], 1 / 3)
        self.assertFalse(summary["superseded_majority_hours_criterion_met"])
        self.assertFalse(summarize(normalized([]))["superseded_majority_hours_criterion_met"])

    def test_network_success_and_source_provenance(self):
        response = Response(json.dumps({"elements": [venue()]}).encode())
        with patch("spoonmaster.discovery.build_opener") as opener:
            opener.return_value.open.return_value = response
            result = fetch_candidates(35.6595, 139.7005)
            request = opener.return_value.open.call_args.args[0]
        self.assertTrue(
            request.full_url.startswith("https://overpass-api.de/api/interpreter?data=")
        )
        self.assertEqual(
            result["candidates"][0]["source_url"], "https://www.openstreetmap.org/node/1"
        )
        self.assertIsNotNone(result["retrieved_at"])

    def test_network_errors_and_limits_are_safe(self):
        cases = [
            (Response(b"x" * (MAX_BYTES + 1)), "response_too_large"),
            (Response(b"[]"), "invalid_source_response"),
            (Response(b"not json"), "invalid_source_response"),
            (Response(b"<html>private error</html>", "text/html"), "unexpected_content_type"),
        ]
        for response, code in cases:
            with self.subTest(code=code), patch("spoonmaster.discovery.build_opener") as opener:
                opener.return_value.open.return_value = response
                with self.assertRaisesRegex(DiscoveryError, code):
                    fetch_candidates(0, 0)
        for error, code in [
            (HTTPError("private", 429, "private", None, None), "source_rate_limited"),
            (HTTPError("private", 302, "private", None, None), "source_http_error"),
            (URLError("private"), "source_unavailable"),
        ]:
            with self.subTest(code=code), patch("spoonmaster.discovery.build_opener") as opener:
                opener.return_value.open.side_effect = error
                with self.assertRaisesRegex(DiscoveryError, f"^{code}$"):
                    fetch_candidates(0, 0)
                if isinstance(error, HTTPError):
                    self.assertTrue(error.closed)

    def test_invalid_inputs_never_reach_network(self):
        for lat, lon, radius in [
            (True, 0, 1),
            ("35;out;", 0, 1),
            (91, 0, 1),
            (0, -181, 1),
            (0, 0, 0),
            (0, 0, 2001),
            (float("nan"), 0, 1),
            (0, 0, float("inf")),
        ]:
            with (
                self.subTest(values=(lat, lon, radius)),
                patch("spoonmaster.discovery.build_opener") as opener,
            ):
                with self.assertRaises(ValueError):
                    fetch_candidates(lat, lon, radius)
                opener.assert_not_called()

    def test_redirects_are_not_followed(self):
        self.assertIsNone(
            NoRedirects().redirect_request(None, None, 302, "", {}, "http://127.0.0.1")
        )

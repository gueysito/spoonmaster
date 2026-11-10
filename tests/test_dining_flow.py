"""Replay owner-reported failures through the owned dining transaction."""

import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from spoonmaster import plugin
from spoonmaster.cards import ride_links
from spoonmaster.dining import Dining, message_chunks
from spoonmaster.discovery import DiscoveryError
from spoonmaster.ledger import LedgerStore
from spoonmaster.recovery import Geocoder, Recovery, mapped
from spoonmaster.verification import Verifier
from tests.test_gates import venue


def request(**updates):
    return {
        "latitude": 35,
        "longitude": 139,
        "origin_confirmed": True,
        "meal": "noodles",
        "area": "Public station",
        "city": "Tokyo",
        "country_code": "JP",
        **updates,
    }


def options():
    return [
        venue(
            f"osm:node:{i}",
            name=f"Example {i}",
            latitude=35 + i / 10000,
            cuisine=cuisine,
            website=None,
            country_code="JP",
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )
        for i, cuisine in enumerate(["ramen", "udon", "soba", "sushi"], 1)
    ]


class DiningFlowTests(unittest.TestCase):
    def setUp(self):
        self.store = LedgerStore()
        self.recovery = Mock()
        self.recovery.discover.return_value = ([], [])
        self.flow = Dining(self.store, None, None, self.recovery)
        self.patches = [
            patch.object(plugin, "verifier", Verifier()),
            patch.object(plugin, "_next_query_at", 0),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def run_flow(self, args=None, data=None):
        with patch.object(
            plugin, "fetch_candidates", return_value={"candidates": data or options()}
        ):
            return json.loads(self.flow.tool(args or request(), session_id="test"))

    def test_noodles_preserve_cuisine_breadth_and_why_without_extra_tool_calls(self):
        result = self.run_flow()
        self.assertEqual([c["cuisine"] for c in result["cards"]], ["ramen", "udon", "soba"])
        self.assertEqual(len(result["cards"]), 3)
        self.assertIn("Pick (provisional)", result["text"])
        self.assertIn("Runner-up (provisional)", result["text"])
        self.assertIn("Wildcard (provisional)", result["text"])
        self.assertIn("https://www.google.com/maps/dir/", result["text"])
        self.assertIsNotNone(self.store.latest("test"))
        self.assertNotIn(
            "No current dining ledger", plugin.why("", _ledger_store=self.store, session_id="test")
        )
        self.assertIn("not evaluated", plugin.why("", _ledger_store=self.store, session_id="test"))
        self.recovery.discover.assert_called_once()

    def test_outage_recovers_once_and_same_pipeline_records_every_option(self):
        self.recovery.discover.return_value = (options()[:3], [])
        with patch.object(
            plugin, "fetch_candidates", side_effect=DiscoveryError("source_http_error")
        ) as fetch:
            result = json.loads(self.flow.tool(request(), session_id="test"))
        fetch.assert_called_once()
        self.recovery.discover.assert_called_once()
        self.assertEqual(len(result["cards"]), 3)
        self.assertIn("source_http_error", result["discovery_gaps"])
        self.assertEqual(self.store.latest("test")["evaluated"], 3)

    def test_all_sources_fail_still_has_honest_explanation_and_no_fabrication(self):
        self.recovery.discover.return_value = ([], ["no_usable_search_excerpts"])
        with patch.object(
            plugin, "fetch_candidates", side_effect=DiscoveryError("source_unavailable")
        ):
            result = json.loads(self.flow.tool(request(meal="bbq"), session_id="test"))
        self.assertFalse(result["cards"])
        self.assertEqual(self.store.latest("test")["evaluated"], 0)
        self.assertIn("couldn't verify nearby options", result["text"])
        self.assertNotIn("widen the radius", result["text"])
        self.assertNotIn("Would you like me to switch", result["text"])

    def test_same_brand_branches_are_not_multiple_choices(self):
        items = options()
        items[0]["brand"] = items[1]["brand"] = "One Restaurant"
        result = self.run_flow(data=items)
        self.assertEqual(len(result["cards"]), 2)
        self.assertEqual(result["empty_slots"], ["wildcard"])

    def test_reset_during_recovery_discards_results_without_posting(self):
        post = Mock()
        self.flow.post = post

        def recover(args):
            self.store.forget("test")
            return options()[:3], []

        self.recovery.discover.side_effect = recover
        with patch.object(
            plugin, "fetch_candidates", side_effect=DiscoveryError("source_unavailable")
        ):
            result = json.loads(self.flow.tool(request(), session_id="test"))
        self.assertEqual(result["error"], "outing_changed")
        self.assertIsNone(self.store.current("test"))
        post.assert_not_called()

    def test_surface_delivery_is_bounded_and_keeps_all_options(self):
        posted = []
        self.flow.post = lambda text: posted.append(text) or SimpleNamespace(ok=True)
        result = self.run_flow()
        self.assertTrue(result["delivered"])
        self.assertTrue(all(len(p) <= 3500 for p in posted))
        for role in ("Pick", "Runner-up", "Wildcard"):
            self.assertIn(role, "\n".join(posted))
        self.assertEqual(message_chunks("x" * 3501), [])

    def test_wrong_session_and_invalid_input_cannot_search_or_reuse_results(self):
        self.run_flow()
        self.assertIsNone(self.store.latest("other"))
        with patch.object(plugin, "fetch_candidates") as fetch:
            for args, error in (
                ({}, "location_required"),
                (request(latitude=True), "invalid_arguments"),
                (request(session_id="other"), "invalid_arguments"),
                (request(area="Tokyo"), "location_required"),
                (request(area="Tokyo approximate city-center search anchor"), "location_required"),
            ):
                self.assertEqual(
                    json.loads(self.flow.tool(args, session_id="test"))["error"], error
                )
            fetch.assert_not_called()

    def test_rides_half_mile_boundary_and_country_appropriate_services(self):
        self.assertFalse(ride_links("ID", 804.672))
        bali = " ".join(ride_links("ID", 805))
        self.assertIn("Grab", bali)
        self.assertIn("Gojek", bali)
        self.assertNotIn("Uber", bali)
        self.assertIn("Uber", " ".join(ride_links("US", 805)))
        self.assertFalse(ride_links("XX", 805))

    def test_immediate_identical_request_reuses_ledger_without_reposting_or_search(self):
        post = Mock(return_value=SimpleNamespace(ok=True))
        self.flow.post = post
        first = self.run_flow()
        calls = post.call_count
        with patch.object(plugin, "fetch_candidates") as fetch:
            second = json.loads(self.flow.tool(request(), session_id="test"))
            fetch.assert_not_called()
        self.assertTrue(second["reused"])
        self.assertEqual(second["search_id"], first["search_id"])
        self.assertEqual(post.call_count, calls)
        self.store.forget("test")
        self.run_flow()
        self.assertGreater(post.call_count, calls)


class RecoveryTests(unittest.TestCase):
    def test_geocoder_bounds_response_and_caches_only_public_query(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"features": []}'
        opener = Mock()
        opener.open.return_value = response
        geocoder = Geocoder()
        with patch("spoonmaster.recovery.build_opener", return_value=opener):
            self.assertEqual(geocoder.lookup("Example BBQ", "Tokyo", "JP"), [])
            self.assertEqual(geocoder.lookup("Example BBQ", "Tokyo", "JP"), [])
        opener.open.assert_called_once()
        call = opener.open.call_args
        self.assertTrue(call.args[0].full_url.startswith("https://photon.komoot.io/api/?"))
        self.assertNotIn("latitude", call.args[0].full_url)
        self.assertIn("lang=en", call.args[0].full_url)
        self.assertEqual(call.kwargs["timeout"], 8)
        response.read.assert_called_once_with(131073)

    def test_geocoder_rejects_oversized_response_without_retry(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b"x" * 131073
        opener = Mock()
        opener.open.return_value = response
        with patch("spoonmaster.recovery.build_opener", return_value=opener):
            with self.assertRaises(DiscoveryError):
                Geocoder().lookup("Example BBQ", "Tokyo", "JP")
        opener.open.assert_called_once()

    def setUp(self):
        self.hit = {
            "title": "Example BBQ",
            "url": "https://example.com/menu",
            "description": "Example BBQ serves barbecue and brisket at its station restaurant.",
        }
        self.item = {"hit": 0, "name": "Example BBQ", "quote": self.hit["description"]}
        self.feature = {
            "geometry": {"type": "Point", "coordinates": [139, 35]},
            "properties": {
                "name": "Example BBQ",
                "countrycode": "JP",
                "osm_key": "amenity",
                "osm_value": "restaurant",
                "osm_type": "N",
                "osm_id": 1,
            },
        }

    def test_extraction_cannot_invent_evidence_and_mapping_must_match(self):
        dispatch = Mock(return_value=json.dumps({"success": True, "data": {"web": [self.hit]}}))
        complete = Mock(return_value=SimpleNamespace(parsed={"venues": [self.item]}))
        geocoder = Mock()
        geocoder.lookup.return_value = [self.feature]
        recovery = Recovery(dispatch, complete, geocoder)
        venues, failures = recovery.discover(request(meal="bbq"))
        self.assertEqual(len(venues), 1)
        self.assertFalse(failures)
        self.assertEqual(venues[0]["discovery_evidence"]["url"], self.hit["url"])
        self.assertEqual(dispatch.call_count, 2)
        self.assertEqual(complete.call_count, 1)
        complete.return_value.parsed = {"venues": [{**self.item, "quote": "Invented barbecue"}]}
        geocoder.reset_mock()
        self.assertFalse(recovery.discover(request(meal="bbq"))[0])
        geocoder.lookup.assert_not_called()

    def test_wrong_country_name_radius_and_invalid_coordinate_are_rejected(self):
        for feature in (
            {**self.feature, "properties": {**self.feature["properties"], "countrycode": "US"}},
            {**self.feature, "properties": {**self.feature["properties"], "name": "Wrong Place"}},
            {**self.feature, "geometry": {"type": "Point", "coordinates": [0, 0]}},
            {**self.feature, "geometry": {"type": "Point", "coordinates": [139, True]}},
        ):
            self.assertIsNone(mapped(feature, self.item, self.hit, request(meal="bbq")))

    def test_missing_excerpts_never_call_extraction_or_geocoder(self):
        dispatch = Mock(
            return_value=json.dumps(
                {"success": True, "data": {"web": [{**self.hit, "description": ""}]}}
            )
        )
        complete, geocoder = Mock(), Mock()
        result, gaps = Recovery(dispatch, complete, geocoder).discover(request())
        self.assertFalse(result)
        self.assertIn("no_usable_search_excerpts", gaps)
        complete.assert_not_called()
        geocoder.lookup.assert_not_called()

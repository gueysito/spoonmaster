"""Outing constraints exercise discovery, gates, cards and private selection together."""

import copy
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from spoonmaster import plugin
from spoonmaster.discovery import normalize_candidates
from spoonmaster.gates import build_ledger
from spoonmaster.household import valid_household
from spoonmaster.ledger import LedgerStore
from spoonmaster.venue_web import PageError
from spoonmaster.verification import Verifier
from tests.test_discovery import venue as osm
from tests.test_gates import NOW, SEARCH, checks, venue


class HouseholdTests(unittest.TestCase):
    def evaluate(self, household, claims=None, **request):
        item = venue(household_claims=claims or {})
        return build_ledger(
            [item],
            SEARCH,
            {},
            {"household": household, "origin_confirmed": True, **request},
            now=NOW,
        )["entries"][0]

    def test_discovery_retains_only_exact_supported_source_claims(self):
        tags = {"min_age": "18", "max_age": "120", "highchair": "no", "diet:vegan": "no"}
        result = normalize_candidates({"elements": [osm(**tags)]}, 35.6595, 139.7005, 1600)
        self.assertEqual(
            result["candidates"][0]["household_claims"],
            {
                "min_age": 18,
                "max_age": 120,
                "highchair": "no",
                "diet:vegan": "no",
            },
        )
        bad = {"min_age": "18+", "max_age": "121", "highchair": {}, "diet:vegan": ["no"]}
        result = normalize_candidates({"elements": [osm(**bad)]}, 35.6595, 139.7005, 1600)
        self.assertEqual(result["candidates"][0]["household_claims"], {})

    def test_age_conflict_excludes_but_missing_or_conflicting_limits_stay_unknown(self):
        household = {"members": [{"age": 7}]}
        entry = self.evaluate(household, {"min_age": 18})
        self.assertIn("household", entry["failed_gates"])
        self.assertIn("member_1.age", checks(entry)["household"]["reason"])
        for claims in ({}, {"min_age": 0}, {"min_age": 18, "max_age": 5}):
            self.assertEqual(
                checks(self.evaluate(household, claims))["household"]["result"], "unknown"
            )
        self.assertIn(
            "household", self.evaluate({"members": [{"age": 70}]}, {"max_age": 60})["failed_gates"]
        )

    def test_diet_no_excludes_yes_and_allergies_never_claim_safety(self):
        household = {"members": [{"dietary_restrictions": ["vegan"]}]}
        self.assertIn(
            "diet_and_vetoes", self.evaluate(household, {"diet:vegan": "no"})["failed_gates"]
        )
        for value in ("yes", "only", "limited", None):
            entry = self.evaluate(household, {"diet:vegan": value}, dietary_restrictions=[])
            self.assertEqual(checks(entry)["diet_and_vetoes"]["result"], "unknown")
        allergy = {"members": [{"dietary_restrictions": ["peanut allergy"]}]}
        entry = self.evaluate(allergy, {"diet:vegan": "only"}, dietary_restrictions=[])
        self.assertEqual(checks(entry)["diet_and_vetoes"]["result"], "unknown")
        self.assertNotIn("peanut", json.dumps(entry))

    def test_empty_outing_diet_does_not_erase_member_restrictions(self):
        entry = self.evaluate({"members": [{}]}, dietary_restrictions=[])
        self.assertEqual(checks(entry)["diet_and_vetoes"]["result"], "unknown")
        entry = self.evaluate({"members": [{"dietary_restrictions": []}]}, dietary_restrictions=[])
        self.assertEqual(checks(entry)["diet_and_vetoes"]["result"], "pass")

    def test_every_members_venue_veto_is_enforced(self):
        entry = self.evaluate({"members": [{}, {"excluded_venue_ids": ["osm:node:1"]}]})
        self.assertEqual(entry["failed_gates"], ["diet_and_vetoes"])
        self.assertIn("member_2.venue_veto", checks(entry)["diet_and_vetoes"]["reason"])

    def test_hard_and_soft_highchair_rules_have_different_exclusion_behavior(self):
        for strength in ("hard", "soft"):
            entry = self.evaluate(
                {
                    "members": [],
                    "rules": [
                        {"kind": "highchair", "strength": strength, "value": True},
                    ],
                },
                {"highchair": "no"},
            )
            self.assertEqual("household" in entry["failed_gates"], strength == "hard")
            self.assertEqual(checks(entry)["household"]["rules"][0]["result"], "fail")

    def test_deadline_compares_absolute_instants_with_exclusive_boundary(self):
        household = {
            "members": [],
            "rules": [
                {"kind": "arrive_before", "strength": "hard", "value": "2026-11-08T20:00:00+09:00"},
            ],
        }
        for arrival, expected in (
            ("2026-11-08T10:59:59Z", "pass"),
            ("2026-11-08T11:00:00Z", "fail"),
        ):
            entry = self.evaluate(household, expected_arrival=arrival)
            self.assertEqual(checks(entry)["household"]["rules"][0]["result"], expected)
        self.assertEqual(checks(self.evaluate(household))["household"]["result"], "unknown")

    def test_mode_and_wait_limits_do_not_fabricate_route_queue_or_parking(self):
        entry = self.evaluate(
            {
                "members": [],
                "rules": [
                    {"kind": "max_wait_minutes", "strength": "hard", "value": 10},
                    {"kind": "max_travel_minutes", "strength": "soft", "value": 15},
                    {"kind": "parking", "strength": "hard", "value": True},
                ],
            },
            travel_mode="driving",
        )
        self.assertEqual(checks(entry)["travel"]["mode"], "driving")
        self.assertEqual(checks(entry)["travel"]["result"], "unknown")
        self.assertEqual(checks(entry)["household"]["result"], "unknown")
        self.assertFalse(entry["failed_gates"])

    def test_strict_bounds_and_no_injected_member_identity_or_verdicts(self):
        invalid = [
            None,
            [],
            {},
            {"members": [False]},
            {"members": [{}] * 13},
            {"members": [{"age": True}]},
            {"members": [{"age": -1}]},
            {"members": [{"age": 121}]},
            {"members": [{"age": "7"}]},
            {"members": [{"name": "private"}]},
            {"members": [{"dietary_restrictions": ["x\n"]}]},
            {"members": [], "rules": [{"kind": [], "strength": "hard", "value": True}]},
            {"members": [], "rules": [{"kind": "highchair", "strength": "hard", "value": 1}]},
            {
                "members": [],
                "rules": [{"kind": "max_wait_minutes", "strength": "hard", "value": True}],
            },
            {
                "members": [],
                "rules": [{"kind": "arrive_before", "strength": "hard", "value": "2026-11-08"}],
            },
            {"members": [], "result": "pass"},
        ]
        for item in invalid:
            with self.subTest(item=item):
                self.assertFalse(valid_household(item))
                result = json.loads(
                    plugin.recommend_candidates(
                        {
                            "search_id": "a" * 24,
                            "origin_confirmed": True,
                            "household": item,
                        },
                        session_id="test",
                    )
                )
                self.assertEqual(result["error"], "invalid_arguments")

    def test_stale_claims_cannot_exclude_and_cuisine_does_not_prove_diet(self):
        item = venue(
            cuisine="vegan",
            household_claims={"min_age": 18, "diet:vegan": "no"},
            retrieved_at="2000-01-01T00:00:00Z",
        )
        request = {"household": {"members": [{"age": 7, "dietary_restrictions": ["vegan"]}]}}
        entry = build_ledger([item], SEARCH, {}, request, now=NOW)["entries"][0]
        self.assertFalse(entry["failed_gates"])
        self.assertEqual(checks(entry)["diet_and_vetoes"]["result"], "unknown")

    def test_real_tool_flow_retains_warnings_and_mode_without_raw_household_data(self):
        store = LedgerStore()
        items = [venue(website=None, retrieved_at=datetime.now(timezone.utc).isoformat())]
        identifier = store.remember(
            "private", {"candidates": items, "candidates_in_radius": 1}, SEARCH
        )
        verifier = Verifier(fetch=lambda url: (_ for _ in ()).throw(PageError("unavailable")))
        verifier.remember(items)
        args = {
            "search_id": identifier,
            "origin_confirmed": True,
            "travel_mode": "driving",
            "household": {
                "members": [{"age": 8, "dietary_restrictions": ["peanut allergy"]}],
                "rules": [{"kind": "parking", "strength": "hard", "value": True}],
            },
        }
        original = copy.deepcopy(args)
        with patch.object(plugin, "verifier", verifier):
            result = json.loads(
                plugin.recommend_candidates(args, _ledger_store=store, session_id="private")
            )
            self.assertEqual(len(result["cards"]), 1)
            self.assertIn("member_1.diet_1", result["cards"][0]["text"])
            self.assertIn("travelmode=driving", result["cards"][0]["directions_url"])
            selection = {"search_id": identifier, "venue_id": items[0]["venue_id"]}
            chosen = json.loads(
                plugin.select_venue(selection, _ledger_store=store, session_id="private")
            )
            self.assertEqual(
                chosen["card"]["household_warnings"], result["cards"][0]["household_warnings"]
            )
            denied = json.loads(
                plugin.select_venue(selection, _ledger_store=store, session_id="other")
            )
            self.assertEqual(denied["error"], "search_not_available")
        self.assertEqual(args, original)
        saved = json.dumps(store.current("private"))
        self.assertNotIn("peanut", saved)
        self.assertNotIn('"age"', saved)
        self.assertNotIn('"members"', saved)
        store.forget("private")
        self.assertIsNone(store.current("private"))

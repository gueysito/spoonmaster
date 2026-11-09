"""Real SQLite, consent, private identity and outing isolation for saved dining parties."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from spoonmaster.companions import CompanionService, CompanionStore
from spoonmaster.ledger import LedgerStore
from spoonmaster.taste import TasteError, TasteStore
from spoonmaster.taste_rank import companion_matches
from spoonmaster.taste_service import TasteService
from tests.test_gates import SEARCH, venue

FAMILY = {
    "members": [
        {"age": 8, "dietary_restrictions": ["peanut allergy"], "liked_cuisines": ["ramen"]},
        {"age": 35, "dietary_restrictions": [], "liked_cuisines": ["sushi"]},
    ]
}


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "data"
        self.clock = [0]
        self.ledgers = LedgerStore(clock=lambda: self.clock[0])
        self.taste = TasteService(
            lambda: self.directory,
            self.ledgers,
            clock=lambda: self.clock[0],
            identity=lambda session: None,
        )
        self.taste.bind("chat", "local-cli")
        self.flow = CompanionService(self.taste)
        self.store = CompanionStore(self.directory / "taste.sqlite3")

    def tool(self, args, session="chat"):
        return json.loads(self.flow.tool(args, session_id=session))

    def command(self, args, session="chat", **kwargs):
        return self.flow.command(args, session_id=session, platform="cli", **kwargs)

    def prepare(self, label="family", household=None):
        return self.tool(
            {
                "action": "prepare",
                "label": label,
                "household": FAMILY if household is None else household,
            }
        )

    def save(self, label="family", household=None):
        preview = self.prepare(label, household)
        return json.loads(self.command(preview["confirmation"].removeprefix("/spoon ")))

    def search(self):
        return self.ledgers.remember(
            "chat", {"candidates": [venue()], "candidates_in_radius": 1}, SEARCH
        )

    def recall(self, identifier, members=None):
        return self.tool(
            {
                "action": "recall",
                "label": "family",
                "search_id": identifier,
                "members": members or [1, 2],
            }
        )

    def activate(self):
        self.save()
        identifier = self.search()
        preview = self.recall(identifier)
        self.command(preview["confirmation"].removeprefix("/spoon "))
        return identifier

    def capture(self, args, **kwargs):
        return json.dumps(args)

    def test_prepare_is_transient_and_sensitive_consent_cannot_be_a_tool_argument(self):
        preview = self.prepare()
        self.assertFalse(self.directory.exists())
        self.assertEqual(preview["preview"]["after"], FAMILY)
        self.assertIn("save-sensitive", preview["confirmation"])
        command = preview["confirmation"].removeprefix("/spoon ")
        denied = json.loads(self.command(command.replace("save-sensitive", "save")))
        self.assertEqual(denied["error"], "sensitive_consent_required")
        self.assertFalse(self.directory.exists())
        self.assertEqual(
            self.tool({"action": "save", "label": "family", "consent": True})["error"],
            "invalid_arguments",
        )
        self.assertTrue(json.loads(self.command(command))["saved"])
        self.assertEqual(self.store.read("local-cli")["family"]["household"], FAMILY)
        self.assertIsNone(TasteStore(self.store.path).read("local-cli"))
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)

    def test_new_sessions_recall_available_groups_without_activating_them(self):
        self.save()
        self.taste.bind("later", "local-cli")
        later = CompanionService(self.taste)
        context = later.before_turn(session_id="later", user_message="dinner with family")
        self.assertIn("family", context["context"])
        self.assertNotIn("peanut", context["context"])
        self.assertEqual(later.active, {})
        self.assertEqual(self.tool({"action": "list"})["groups"], ["family"])
        self.assertEqual(
            self.tool({"action": "view", "label": "family"})["group"]["household"], FAMILY
        )

    def test_recall_subset_requires_confirmation_and_only_changes_one_search(self):
        self.save()
        identifier = self.search()
        preview = self.recall(identifier, [2])
        args = {"search_id": identifier, "origin_confirmed": True}
        self.assertNotIn(
            "household", json.loads(self.flow.wrap(self.capture, args, session_id="chat"))
        )
        self.command(preview["confirmation"].removeprefix("/spoon "))
        result = json.loads(self.flow.wrap(self.capture, args, session_id="chat"))
        self.assertEqual(result["household"]["members"], [FAMILY["members"][1]])
        next_id = self.search()
        result = json.loads(
            self.flow.wrap(self.capture, {**args, "search_id": next_id}, session_id="chat")
        )
        self.assertNotIn("household", result)
        self.assertEqual(self.store.read("local-cli")["family"]["household"], FAMILY)

    def test_correction_preserves_other_groups_and_returns_exact_diff(self):
        self.save()
        self.save("coworkers", {"members": [{"liked_cuisines": ["sushi"]}]})
        coworker = self.store.read("local-cli")["coworkers"]
        corrected = copy.deepcopy(FAMILY)
        corrected["members"][0]["age"] = 9
        result = self.save(household=corrected)
        self.assertEqual(result["diff"]["before"], FAMILY)
        self.assertEqual(result["diff"]["after"], corrected)
        self.assertEqual(self.store.read("local-cli")["coworkers"], coworker)

    def test_wrong_session_owner_shared_chat_and_forged_scope_cannot_confirm(self):
        preview = self.prepare()
        command = preview["confirmation"].removeprefix("/spoon ")
        self.assertEqual(
            json.loads(self.command(command, "other"))["error"], "confirmation_expired"
        )
        group = SimpleNamespace(chat_type="group", platform="telegram", user_id="fixture")
        self.assertIn("private", self.command(command, source=group))
        self.taste.bind("intruder", "other-owner")
        self.assertEqual(self.tool({"action": "list"}, "intruder")["groups"], [])
        self.assertEqual(
            self.tool(
                {"action": "prepare", "label": "family", "household": FAMILY, "owner": "local-cli"}
            )["error"],
            "invalid_arguments",
        )
        self.assertFalse(self.directory.exists())

    def test_stale_confirmation_and_changed_profile_fail_closed(self):
        self.save()
        identifier = self.search()
        preview = self.recall(identifier)
        prior = self.store.read("local-cli")["family"]
        self.store.save_group("local-cli", "family", {"members": []}, prior["revision"])
        result = json.loads(self.command(preview["confirmation"].removeprefix("/spoon ")))
        self.assertEqual(result["error"], "companions_changed")
        self.assertFalse(self.flow.active)

    def test_other_process_deletion_invalidates_active_outing(self):
        identifier = self.activate()
        self.store.delete_group("local-cli", "family")
        result = json.loads(
            self.flow.wrap(self.capture, {"search_id": identifier}, session_id="chat")
        )
        self.assertEqual(result["error"], "companions_changed")
        self.assertIsNone(self.ledgers.current("chat"))

    def test_concurrent_change_does_not_return_an_old_recommendation(self):
        identifier = self.activate()

        def changed(args, **kwargs):
            self.store.delete_group("local-cli", "family")
            return json.dumps({"cards": ["old"]})

        result = json.loads(self.flow.wrap(changed, {"search_id": identifier}, session_id="chat"))
        self.assertNotIn("cards", result)
        self.assertEqual(result["error"], "companions_changed")

    def test_solo_reset_expiry_and_profile_delete_remove_outing_context(self):
        self.activate()
        self.command("companions solo")
        self.assertFalse(self.flow.active)
        self.assertIsNone(self.ledgers.current("chat"))
        self.assertIn("family", self.store.read("local-cli"))
        self.activate()
        self.clock[0] += 901
        self.flow.before_turn(session_id="chat")
        self.assertFalse(self.flow.active)
        self.assertIsNone(self.ledgers.current("chat"))
        TasteStore(self.store.path).control("local-cli", "delete")
        self.assertEqual(self.store.read("local-cli"), {})

    def test_failed_save_does_not_claim_success_and_keeps_preview_retryable(self):
        preview = self.prepare()
        command = preview["confirmation"].removeprefix("/spoon ")
        with patch.object(
            CompanionStore, "save_group", side_effect=TasteError("storage_unavailable")
        ):
            result = json.loads(self.command(command))
        self.assertFalse(result["saved"])
        self.assertFalse(self.directory.exists())
        self.assertTrue(json.loads(self.command(command))["saved"])

    def test_deleted_and_recreated_group_cannot_reuse_old_consent(self):
        identifier = self.activate()
        self.store.delete_group("local-cli", "family")
        self.store.save_group("local-cli", "family", FAMILY, None)
        result = json.loads(
            self.flow.wrap(self.capture, {"search_id": identifier}, session_id="chat")
        )
        self.assertEqual(result["error"], "companions_changed")

    def test_only_attending_companions_contribute_preferences(self):
        items = [venue(cuisine="ramen"), venue("osm:node:2", cuisine="sushi")]
        selected = {"members": [FAMILY["members"][1]]}
        ranked = companion_matches(items, selected, {})
        self.assertNotIn("osm:node:1", ranked)
        self.assertEqual(ranked["osm:node:2"]["score"], 2)
        self.assertIn("Companion 1 likes sushi", ranked["osm:node:2"]["reasons"])
        self.assertEqual(companion_matches(items, {}, {}), {})

    def test_outing_can_select_group_rules_without_editing_saved_group(self):
        group = {
            **FAMILY,
            "rules": [
                {"kind": "highchair", "strength": "hard", "value": True},
                {"kind": "max_wait_minutes", "strength": "soft", "value": 15},
            ],
        }
        self.save(household=group)
        identifier = self.search()
        preview = self.tool(
            {
                "action": "recall",
                "label": "family",
                "search_id": identifier,
                "members": [2],
                "rules": [2],
            }
        )
        self.assertEqual(preview["preview"]["household"]["rules"], [group["rules"][1]])
        self.command(preview["confirmation"].removeprefix("/spoon "))
        self.assertEqual(self.store.read("local-cli")["family"]["household"], group)

    def test_reset_and_another_profile_cannot_reuse_pending_confirmation(self):
        preview = self.prepare()
        command = preview["confirmation"].removeprefix("/spoon ")
        self.flow.forget("chat")
        self.assertEqual(json.loads(self.command(command))["error"], "confirmation_expired")
        preview = self.prepare()
        self.taste.state_directory = lambda: self.directory / "other-profile"
        command = preview["confirmation"].removeprefix("/spoon ")
        self.assertEqual(json.loads(self.command(command))["error"], "confirmation_expired")

    def test_corrupt_group_is_not_loaded_but_can_be_deleted(self):
        self.save()
        with self.store.transaction() as db:
            db.execute("UPDATE companions SET data=? WHERE owner=?", ("{}", "local-cli"))
        with self.assertRaises(TasteError):
            self.store.read("local-cli")
        self.command("companions delete family confirm")
        self.assertEqual(self.store.read("local-cli"), {})

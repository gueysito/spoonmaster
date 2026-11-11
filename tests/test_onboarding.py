"""First-use choices, consent, transactional seeding and one-time reminders."""

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

from spoonmaster.onboarding import INTRO, REMINDER, Onboarding
from spoonmaster.onboarding_store import OnboardingStore
from spoonmaster.taste import TasteError, TasteStore
from spoonmaster.taste_service import TasteService
from tests.test_taste import pref
from tests.test_taste_service import dm


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "data"
        self.taste = TasteService(lambda: self.path, identity=lambda s: None)
        self.flow = Onboarding(self.taste)
        self.taste.bind("chat", "local-cli")
        self.store = OnboardingStore(self.path / "taste.sqlite3")

    def command(self, value):
        return self.flow.command(value, session_id="chat", platform="cli")

    def finish(self):
        self.command("personalize")
        for step in range(1, 7):
            result = self.command(f"pick {step} 1")
        return result

    def test_first_offer_does_not_write_and_does_not_repeat(self):
        result = self.flow.before_turn(session_id="chat", user_message="hello")
        self.assertIn("Personalize my picks", result["context"])
        self.assertIn("Find food now", result["context"])
        self.assertFalse(self.path.exists())
        self.assertIsNone(self.flow.before_turn(session_id="chat", user_message="dinner nearby"))
        self.assertFalse(self.path.exists())

    def test_skip_starts_search_without_profile_and_reminds_once_across_restart(self):
        self.assertIn("Let's find you some food", self.command("now"))
        self.assertIsNone(self.store.read("local-cli"))
        self.assertEqual(self.flow.selected("chat"), REMINDER)
        restarted = Onboarding(self.taste)
        self.assertIsNone(restarted.selected("chat"))
        self.assertIsNone(restarted.before_turn(session_id="chat", user_message="hello"))

    def test_no_reminder_or_disk_write_before_any_offer_or_choice(self):
        self.assertIsNone(self.flow.selected("chat"))
        self.assertFalse(self.path.exists())

    def test_six_choices_commit_together_and_completion_suppresses_reminder(self):
        self.command("personalize")
        for step in range(1, 6):
            self.command(f"pick {step} 1")
            self.assertIsNone(self.store.read("local-cli"))
        result = self.command("pick 6 1")
        self.assertIn("You're set", result)
        profile = self.store.read("local-cli")
        self.assertEqual(len(profile["prefs"]), 6)
        self.assertTrue(
            all(p["scope"] == "tentative" and p["polarity"] == 1 for p in profile["prefs"])
        )
        self.assertEqual(profile["prefs"][0]["item"], "burger")
        self.assertEqual(profile["prefs"][1]["item"], "ramen")
        self.assertIsNone(self.flow.selected("chat"))
        self.assertEqual(self.store.status("local-cli")["status"], "complete")

    def test_cancel_midway_does_not_enable_or_save_partial_tastes(self):
        self.command("personalize")
        self.command("pick 1 2")
        self.command("now")
        self.assertIsNone(self.store.read("local-cli"))
        self.assertIn("No active questions", self.command("pick 2 1"))

    def test_existing_preferences_remain_unchanged(self):
        store = TasteStore(self.store.path)
        revision = store.control("local-cli", "enable")["after"]["revision"]
        before = store.feedback("local-cli", [pref("ramen", polarity=-1)], "feedback", revision)[
            "added"
        ][0]
        self.finish()
        profile = store.read("local-cli")
        self.assertEqual(next(p for p in profile["prefs"] if p["id"] == before["id"]), before)
        self.assertEqual(len(profile["prefs"]), 6)

    def test_changed_profile_or_deleted_attempt_cannot_be_overwritten(self):
        self.command("personalize")
        for step in range(1, 6):
            self.command(f"pick {step} 1")
        self.taste.command("enable", platform="cli", session_id="chat")
        result = self.command("pick 6 1")
        self.assertIn("profile_changed", result)
        self.assertEqual(self.store.read("local-cli")["prefs"], [])
        self.command("delete confirm")
        self.assertIsNone(self.store.status("local-cli"))
        self.assertIn("No active questions", self.command("pick 6 1"))

    def test_invalid_or_stale_answer_does_not_advance(self):
        self.command("personalize")
        self.assertIn("different question", self.command("pick 3 1"))
        self.assertIn("2/6", self.command("pick 1 2"))
        self.assertIn("different question", self.command("pick 1 2"))
        self.assertEqual(len(self.flow.drafts["chat"]["choices"]), 1)

    def test_direct_phrase_and_plain_answers_work_without_buttons(self):
        intro = self.flow.before_turn(session_id="chat", user_message="get me onboarded")
        self.assertIn("1/6", intro["context"])
        self.assertIn("save tastes locally", intro["context"])
        self.assertIsNone(self.store.read("local-cli"))
        result = self.flow.before_turn(session_id="chat", user_message="personalize my picks")
        self.assertIn("1/6", result["context"])
        for answer in ("pizza", "2", "1", "skip", "2", "1"):
            result = self.flow.before_turn(session_id="chat", user_message=answer)
        self.assertIn("You're set", result["context"])
        self.assertEqual(len(self.store.read("local-cli")["prefs"]), 5)

    def test_buttons_and_unsupported_button_fallback(self):
        self.flow.ask_choice = Mock(side_effect=["personalize", "1", "2", "1", "1", "2", "1"])
        self.assertIn("You're set", self.command("start"))
        self.assertEqual(self.flow.ask_choice.call_count, 7)
        self.flow.ask_choice = Mock(side_effect=RuntimeError("unavailable"))
        self.assertEqual(self.command("start"), INTRO)

    def test_shared_chat_is_denied_and_wrong_user_cannot_answer(self):
        source = dm()
        source.chat_type = "group"
        result = self.flow.command("personalize", source=source, session_id="shared")
        self.assertIn("private chat", result)
        self.assertFalse(self.path.exists())
        self.command("personalize")
        self.taste.bind("chat", "other-person")
        self.assertIn("No active questions", self.flow.answer("chat", 1, "1"))

    def test_reminder_claim_is_atomic_across_instances(self):
        self.command("now")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda _: OnboardingStore(self.store.path).claim_reminder("local-cli"), range(2)
                )
            )
        self.assertEqual(sorted(results), [False, True])

    def test_store_failure_does_not_block_search_or_claim_saved_tastes(self):
        from unittest.mock import patch

        with patch.object(OnboardingStore, "skip", side_effect=TasteError("storage_unavailable")):
            self.assertIn("searching still works", self.command("now"))
        self.assertIsNone(self.store.read("local-cli"))

    def test_final_hook_save_failure_is_explicit(self):
        from unittest.mock import patch

        self.command("personalize")
        for step in range(1, 6):
            self.command(f"pick {step} 1")
        with patch.object(OnboardingStore, "finish", side_effect=TasteError("storage_unavailable")):
            result = self.flow.before_turn(session_id="chat", user_message="1")
        self.assertIsNotNone(result)
        self.assertIn("couldn't save", result["context"])
        self.assertIsNone(self.store.read("local-cli"))

    def test_existing_profile_without_an_offer_is_not_nagged(self):
        self.taste.command("enable", platform="cli", session_id="chat")
        self.assertIsNone(self.flow.before_turn(session_id="chat", user_message="hello"))
        self.assertIsNone(self.flow.selected("chat"))

    def test_final_write_failure_rolls_back_tastes_and_completion_together(self):
        import sqlite3
        from unittest.mock import patch

        self.command("personalize")
        for step in range(1, 6):
            self.command(f"pick {step} 1")
        with patch.object(
            OnboardingStore, "_write_state", side_effect=sqlite3.OperationalError("fixture")
        ):
            result = self.command("pick 6 1")
        self.assertIn("Nothing new was saved", result)
        self.assertIsNone(self.store.read("local-cli"))
        self.assertEqual(self.store.status("local-cli")["status"], "active")
        self.assertIn("You're set", self.command("pick 6 1"))

    def test_optional_skips_never_invent_preferences(self):
        self.command("personalize")
        for step in range(1, 7):
            result = self.command(f"pick {step} skip")
        self.assertIn("no new preferences", result)
        self.assertEqual(self.store.read("local-cli")["prefs"], [])

    def test_deleting_one_profile_keeps_another_profiles_draft(self):
        self.command("personalize")
        original = self.path
        self.taste.state_directory = lambda: original / "second-profile"
        self.taste.bind("second", "local-cli")
        self.flow.start("second")
        self.taste.state_directory = lambda: original
        self.command("delete confirm")
        self.assertIn("second", self.flow.drafts)


class OnboardingRepairTests(unittest.TestCase):
    setUp = OnboardingTests.setUp
    command = OnboardingTests.command

    def test_explicit_food_request_does_not_interrupt_with_welcome_menu(self):
        self.assertIsNone(
            self.flow.before_turn(session_id="chat", user_message="Find noodles nearby")
        )
        self.assertFalse(self.path.exists())

    def test_natural_tool_questions_use_selectable_clarify_and_finish_atomically(self):
        result = json.loads(self.flow.tool({}, session_id="chat"))
        for step in range(1, 7):
            self.assertEqual(result["next_tool"], "clarify")
            self.assertEqual(result["step"], step)
            labels = result["questions"][0]["choices"]
            self.assertFalse(labels[0].startswith("1. "))
            self.assertFalse(labels[1].startswith("2. "))
            self.assertIn("Skip", labels)
            self.assertIn("Back", labels)
            self.assertIn("Find food now", labels)
            self.assertIsNone(self.store.read("local-cli"))
            result = json.loads(
                self.flow.tool({"action": "answer", "step": step, "choice": "1"}, session_id="chat")
            )
        self.assertTrue(result["complete"])
        self.assertIn("You're set", result["text"])
        self.assertEqual(len(self.store.read("local-cli")["prefs"]), 6)

    def test_typo_and_invalid_text_keep_the_controller_in_charge(self):
        self.command("personalize")
        for step in range(1, 4):
            self.command(f"pick {step} 1")
        result = self.flow.before_turn(session_id="chat", user_message="brght and tangy")
        self.assertEqual(result["action"], "block")
        self.assertIn("5/6", result["message"])
        result = self.flow.before_turn(session_id="chat", user_message="unclear answer")
        self.assertIn("5/6", result["message"])
        self.assertFalse(self.flow.drafts["chat"]["paused"])
        self.assertIsNone(self.store.read("local-cli"))

    def test_back_stale_answer_and_exit_never_partially_save(self):
        self.flow.tool({}, session_id="chat")
        self.flow.tool({"action": "answer", "step": 1, "choice": "1"}, session_id="chat")
        stale = json.loads(
            self.flow.tool({"action": "answer", "step": 1, "choice": "2"}, session_id="chat")
        )
        self.assertEqual(stale["step"], 2)
        back = json.loads(
            self.flow.tool({"action": "answer", "step": 2, "choice": "back"}, session_id="chat")
        )
        self.assertEqual(back["step"], 1)
        self.assertTrue(
            json.loads(self.flow.tool({"action": "now"}, session_id="chat"))["complete"]
        )
        self.assertIsNone(self.store.read("local-cli"))

    def test_personalize_command_uses_picker_without_intro_or_typing_commands(self):
        self.flow.ask_choice = Mock(side_effect=["1"] * 6)
        result = self.command("personalize")
        self.assertIn("You're set", result)
        self.assertEqual(self.flow.ask_choice.call_count, 6)
        first = self.flow.ask_choice.call_args_list[0]
        self.assertIn("1/6", first.args[0])
        self.assertEqual(first.args[1][0]["label"], "burger")

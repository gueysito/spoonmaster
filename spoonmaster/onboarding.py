"""Optional first-use onboarding with bounded transient answers and portable text choices."""

import json
import threading
import time

from .cards import plain
from .onboarding_store import OnboardingStore
from .taste import TasteError
from .taste_service import owner_key

INTRO = (
    "Welcome to Spoonmaster. Choose one:\n"
    "1. Personalize my picks: /spoon personalize\n"
    "2. Find food now: /spoon now\n"
    "Personalizing takes six quick choices and saves tastes locally for future sessions, "
    "then learns from your choices and feedback. Tastes may reach your model provider. "
    "You can view, correct or delete them anytime. Skipping saves only your onboarding "
    "choice/reminder status, not tastes."
)
FIND_NOW = "Let's find food. Share a location or area if you haven't already, and what sounds good."
REMINDER = (
    "Want more personal picks? Say ‘get me onboarded’ anytime. "
    "A few quick questions, then I learn from your choices and feedback."
)
PAIRS = (
    ("For a relaxed meal?", "dish", "burger", "pizza"),
    ("Which sounds better most often?", "cuisine", "ramen", "sushi"),
    ("Which texture do you enjoy?", "attribute", "crispy", "soft"),
    ("Which flavor style?", "attribute", "bright and tangy", "rich and creamy"),
    ("Which atmosphere?", "vibe", "lively", "quiet"),
    ("When choosing food?", "attribute", "familiar favorites", "trying something new"),
)


class Onboarding:
    def __init__(self, taste, ask_choice=None, clock=time.monotonic):
        self.taste = taste
        self.ask_choice = ask_choice
        self.clock = clock
        self.drafts = {}
        self.offered = {}
        self.lock = threading.RLock()

    def _prune(self):
        for mapping in (self.drafts, self.offered):
            for key in list(mapping):
                if self.clock() - mapping[key]["time"] >= 7200:
                    del mapping[key]
            while len(mapping) > 100:
                mapping.pop(next(iter(mapping)))

    def forget(self, session_id=None, **kwargs):
        with self.lock:
            self.drafts.pop(session_id, None)

    def _access(self, session):
        owner, path = self.taste.binding(session)
        return owner, path, OnboardingStore(path), self.taste.scope_key(owner, path)

    def _question(self, draft):
        index = len(draft["choices"])
        question, _, first, second = PAIRS[index]
        return (
            f"{index + 1}/6: {question}\n1. {first}\n2. {second}\n"
            f"Reply 1, 2 or skip, or use /spoon pick {index + 1} 1|2|skip. "
            "You can switch to /spoon now anytime."
        )

    def start(self, session):
        owner, path, store, scope = self._access(session)
        with self.lock:
            self._prune()
            result = store.begin(owner)
            draft = {
                **result,
                "owner": owner,
                "path": path,
                "scope": scope,
                "choices": [],
                "time": self.clock(),
                "paused": False,
            }
            self.drafts[session] = draft
            self._prune()
            return (
                "These six choices will save tastes locally for future sessions and may reach "
                "your model provider. You can switch to food now without saving tastes.\n"
                + self._question(draft)
            )

    def skip(self, session):
        self.forget(session)
        owner, _, store, scope = self._access(session)
        with self.lock:
            self.offered[scope] = {"time": self.clock()}
            self._prune()
        try:
            store.skip(owner)
            return FIND_NOW
        except TasteError:
            return FIND_NOW + " I couldn't save the onboarding choice; searching still works."

    def answer(self, session, step, answer):
        owner, path, store, scope = self._access(session)
        with self.lock:
            self._prune()
            draft = self.drafts.get(session)
            if not draft or draft["scope"] != scope:
                return "No active questions here. Use /spoon start."
            if step != len(draft["choices"]) + 1 or answer not in ("1", "2", "skip"):
                return "That answer is for a different question. " + self._question(draft)
            state = store.status(owner)
            if not state or state["attempt"] != draft["attempt"]:
                self.drafts.pop(session, None)
                return "Onboarding changed or was deleted. Use /spoon start when ready."
            pair = PAIRS[step - 1]
            selected = (
                None
                if answer == "skip"
                else {
                    "item": pair[int(answer) + 1],
                    "kind": pair[1],
                    "polarity": 1,
                    "scope": "tentative",
                    "context": {},
                }
            )
            choices = draft["choices"] + [selected]
            if len(choices) < len(PAIRS):
                draft.update(choices=choices, paused=False)
                return self._question(draft)
            # Do not advance the draft on a failed commit: the final answer can be retried.
            diff = store.finish(owner, draft["attempt"], draft["revision"], choices)
            self.drafts.pop(session, None)
            self.taste.invalidate(owner, path)
            added = ", ".join(plain(item["item"]) for item in diff["added"]) or "no new preferences"
            return (
                f"You're set. Saved starting preferences: {added}. "
                f"Kept {len(diff['retained_existing'])} existing matching preferences unchanged. "
                "These are tentative likes, not dislikes of the other choices. "
                "View or change them with /spoon profile. "
                "Any dietary restrictions for this outing? Optional; health details aren't saved."
            )

    def selected(self, session):
        try:
            owner, _, store, scope = self._access(session)
            state = store.status(owner)
            with self.lock:
                self._prune()
                offered = scope in self.offered
            if state is None and offered:
                store.skip(owner)
            return REMINDER if store.claim_reminder(owner) else None
        except TasteError:
            return None  # A reminder/storage failure must never block the selected venue.

    def before_turn(self, session_id=None, user_message="", **kwargs):
        if not isinstance(user_message, str):
            return None
        try:
            owner, _, store, scope = self._access(session_id)
            message = user_message.strip().casefold()
            if message == "find food now":
                response = self.skip(session_id)
            elif message == "personalize my picks":
                response = self.start(session_id)
            elif message == "get me onboarded":
                response = INTRO
            else:
                with self.lock:
                    self._prune()
                    draft = self.drafts.get(session_id)
                    if draft and draft["scope"] == scope and not draft["paused"]:
                        step = len(draft["choices"]) + 1
                        pair = PAIRS[step - 1]
                        choice = {
                            "1": "1",
                            "2": "2",
                            "skip": "skip",
                            pair[2]: "1",
                            pair[3]: "2",
                            "neither": "skip",
                        }.get(message)
                        if choice:
                            response = self.answer(session_id, step, choice)
                            return {"context": "Spoonmaster onboarding response: " + response}
                        draft["paused"] = True
                    if scope in self.offered:
                        return None
                    self.offered[scope] = {"time": self.clock()}
                    self._prune()
                if store.status(owner) is not None or self.taste.read(session_id) is not None:
                    return None
                response = INTRO
            with self.lock:
                self.offered[scope] = {"time": self.clock()}
                self._prune()
            return {
                "context": "Relay this Spoonmaster onboarding response. Do not block an "
                "explicit food search or repeat a supplied location. " + response
            }
        except TasteError:
            return None

    def _ask(self, question, choices):
        try:
            return self.ask_choice(question, choices) if self.ask_choice else None
        except (RuntimeError, ValueError, TypeError):
            return None

    def _interactive(self, session):
        if not self.ask_choice:
            return INTRO
        choice = self._ask(
            INTRO,
            [
                {"value": "personalize", "label": "Personalize my picks"},
                {"value": "now", "label": "Find food now"},
            ],
        )
        if choice == "now":
            return self.skip(session)
        if choice != "personalize":
            return INTRO
        response = self.start(session)
        for step in range(1, len(PAIRS) + 1):
            pair = PAIRS[step - 1]
            choice = self._ask(
                response,
                [
                    {"value": "1", "label": pair[2]},
                    {"value": "2", "label": pair[3]},
                    {"value": "skip", "label": "Skip this question"},
                ],
            )
            if choice not in ("1", "2", "skip"):
                return response
            response = self.answer(session, step, choice)
        return response

    def command(self, raw_args, *, source=None, platform=None, session_id=None, **kwargs):
        parts = raw_args.split() if isinstance(raw_args, str) else []
        actions = {"start", "personalize", "now", "pick"}
        if not parts or parts[0] not in actions:
            result = self.taste.command(
                raw_args, source=source, platform=platform, session_id=session_id, **kwargs
            )
            if parts == ["delete", "confirm"] and '"deleted": true' in result:
                owner = owner_key(source, platform)
                with self.lock:
                    for key in list(self.drafts):
                        if self.drafts[key]["owner"] == owner:
                            del self.drafts[key]
            return result
        owner = owner_key(source, platform)
        if owner is None or not session_id:
            return "Onboarding requires a private chat or local CLI. Food search remains available."
        try:
            self.taste.bind(session_id, owner)
            if parts == ["start"]:
                return self._interactive(session_id)
            if parts == ["personalize"]:
                return self.start(session_id)
            if parts == ["now"]:
                return self.skip(session_id)
            if len(parts) == 3 and parts[0] == "pick" and parts[1] in tuple("123456"):
                return self.answer(session_id, int(parts[1]), parts[2])
            return "Use /spoon start, /spoon now or /spoon pick <question> 1|2|skip."
        except TasteError as error:
            return "Nothing new was saved: " + str(error) + ". You can still use /spoon now."

    def selection_tool(self, handler, args, **kwargs):
        result = json.loads(handler(args, **kwargs))
        if result.get("card") and result.get("proceed"):
            reminder = self.selected(kwargs.get("session_id"))
            if reminder:
                result["onboarding_reminder"] = reminder
                result["card"]["text"] += "\n\n" + reminder
        return json.dumps(result, ensure_ascii=False)

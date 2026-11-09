"""Atomic onboarding markers and profile seeding; answers stay transient until completion."""

import json
import secrets
from datetime import datetime, timezone

from .taste import MAX_PREFS, TasteError, TasteStore, identifier, preference


class OnboardingStore(TasteStore):
    def _state(self, db, owner):
        if (
            db is None
            or not db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='onboarding'"
            ).fetchone()
        ):
            return None
        row = db.execute("SELECT data FROM onboarding WHERE owner=?", (owner,)).fetchone()
        if not row:
            return None
        if len(row[0]) > 1000:
            raise TasteError("corrupt_onboarding")
        state = json.loads(row[0])
        if (
            not isinstance(state, dict)
            or set(state) != {"status", "attempt", "reminded"}
            or state["status"] not in ("active", "skipped", "complete")
            or type(state["reminded"]) is not bool
            or (
                state["status"] == "active"
                and (not isinstance(state["attempt"], str) or len(state["attempt"]) != 24)
            )
            or (state["status"] != "active" and state["attempt"] is not None)
        ):
            raise TasteError("corrupt_onboarding")
        return state

    def _write_state(self, db, owner, state):
        db.execute(
            "CREATE TABLE IF NOT EXISTS onboarding (owner TEXT PRIMARY KEY, data TEXT NOT NULL)"
        )
        if not db.execute("SELECT 1 FROM onboarding WHERE owner=?", (owner,)).fetchone():
            if db.execute("SELECT count(*) FROM onboarding").fetchone()[0] >= 100:
                raise TasteError("onboarding_store_full")
        db.execute("INSERT OR REPLACE INTO onboarding VALUES (?, ?)", (owner, json.dumps(state)))

    def status(self, owner):
        with self.transaction() as db:
            return self._state(db, owner)

    def begin(self, owner):
        with self.transaction(create=True) as db:
            profile = self._get(db, owner)
            state = {"status": "active", "attempt": secrets.token_hex(12), "reminded": False}
            self._write_state(db, owner, state)
            return {
                "attempt": state["attempt"],
                "revision": profile["revision"] if profile else None,
            }

    def skip(self, owner):
        with self.transaction(create=True) as db:
            old = self._state(db, owner)
            if old and old["status"] == "complete":
                return
            self._write_state(
                db,
                owner,
                {"status": "skipped", "attempt": None, "reminded": bool(old and old["reminded"])},
            )

    def claim_reminder(self, owner):
        with self.transaction() as db:
            state = self._state(db, owner)
            if not state or state["status"] != "skipped" or state["reminded"]:
                return False
            state["reminded"] = True
            self._write_state(db, owner, state)
            return True

    def finish(self, owner, attempt, revision, choices):
        if not isinstance(choices, list) or len(choices) != 6:
            raise TasteError("incomplete_onboarding")
        prepared = [preference(item) for item in choices if item is not None]
        with self.transaction() as db:
            state = self._state(db, owner)
            if not state or state["status"] != "active" or state["attempt"] != attempt:
                raise TasteError("onboarding_changed")
            profile = self._get(db, owner)
            if (profile["revision"] if profile else None) != revision:
                raise TasteError("profile_changed")
            if profile is None:
                if db.execute("SELECT count(*) FROM profiles").fetchone()[0] >= 100:
                    raise TasteError("store_full")
                profile = {"version": 1, "revision": 0, "enabled": True, "prefs": []}
            added, retained = [], []
            for item in prepared:
                item.update(
                    scope="tentative",
                    polarity=1,
                    provenance="onboarding",
                    confidence="reported_once",
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
                item["id"] = identifier(item)
                if any(p["id"] == item["id"] for p in profile["prefs"]):
                    retained.append(item["id"])
                else:
                    profile["prefs"].append(item)
                    added.append(item)
            if len(profile["prefs"]) > MAX_PREFS:
                raise TasteError("profile_full")
            profile["enabled"] = True
            profile["revision"] += 1
            self._save(db, owner, profile)
            self._write_state(db, owner, {"status": "complete", "attempt": None, "reminded": True})
            return {
                "revision": profile["revision"],
                "added": added,
                "changed": [],
                "retained_existing": retained,
                "held_situational": [],
                "rejected_inferences": [],
            }

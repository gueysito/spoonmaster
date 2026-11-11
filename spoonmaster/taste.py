"""Small transactional taste store. No location history or raw feedback transcripts."""

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

KINDS = ("dish", "attribute", "cuisine", "venue", "vibe")
SCOPES = ("durable", "situational", "tentative")
CONTEXT_KEYS = ("season", "time", "occasion", "company")
MAX_PREFS = 100


class TasteError(Exception):
    pass


def text(value, maximum=100):
    return (
        isinstance(value, str)
        and 1 <= len(value) <= maximum
        and value == value.strip()
        and all(c.isprintable() for c in value)
    )


def preference(value):
    if not isinstance(value, dict) or set(value) != {
        "item",
        "kind",
        "polarity",
        "scope",
        "context",
    }:
        raise TasteError("invalid_preference")
    if (
        not text(value["item"])
        or value["kind"] not in KINDS
        or type(value["polarity"]) is not int
        or value["polarity"] not in (-1, 0, 1)
        or value["scope"] not in SCOPES
        or not isinstance(value["context"], dict)
        or set(value["context"]) - set(CONTEXT_KEYS)
        or any(not text(v, 40) for v in value["context"].values())
    ):
        raise TasteError("invalid_preference")
    if value["scope"] == "situational" and not value["context"]:
        raise TasteError("situational_context_required")
    return dict(value, context=dict(value["context"]))


def identifier(value):
    identity = [value["kind"], value["item"].casefold(), value["scope"], value["context"]]
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]


def validate_profile(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "revision", "enabled", "prefs"}
        or type(value["version"]) is not int
        or value["version"] != 1
        or type(value["revision"]) is not int
        or value["revision"] < 0
        or type(value["enabled"]) is not bool
        or not isinstance(value["prefs"], list)
        or len(value["prefs"]) > MAX_PREFS
    ):
        raise TasteError("corrupt_profile")
    ids = set()
    for item in value["prefs"]:
        if not isinstance(item, dict) or set(item) != {
            "id",
            "item",
            "kind",
            "polarity",
            "scope",
            "context",
            "confidence",
            "provenance",
            "updated_at",
        }:
            raise TasteError("corrupt_profile")
        preference({k: item[k] for k in ("item", "kind", "polarity", "scope", "context")})
        if (
            item["id"] != identifier(item)
            or item["id"] in ids
            or item["confidence"] not in ("user_confirmed", "reported_once")
            or item["provenance"] not in ("feedback", "explicit", "onboarding", "correction")
            or not text(item["updated_at"], 40)
        ):
            raise TasteError("corrupt_profile")
        ids.add(item["id"])
    return value


class TasteStore:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def transaction(self, create=False):
        connection = None
        try:
            if not create and not self.path.exists():
                yield None
                return
            if self.path.is_symlink() or self.path.parent.is_symlink():
                raise TasteError("storage_unavailable")
            if create:
                self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                fd = (
                    os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    if not self.path.exists()
                    else None
                )
                if fd is not None:
                    os.close(fd)
            connection = sqlite3.connect(self.path, timeout=2, isolation_level=None)
            connection.execute("PRAGMA secure_delete=ON")
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise TasteError("unsupported_store_version")
            if version == 0:
                if not create:
                    raise TasteError("corrupt_profile")
                connection.execute(
                    "CREATE TABLE profiles (owner TEXT PRIMARY KEY, data TEXT NOT NULL)"
                )
                connection.execute("PRAGMA user_version=1")
            yield connection
            connection.commit()
        except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, RecursionError) as error:
            raise TasteError("storage_unavailable") from error
        finally:
            if connection is not None:
                connection.close()  # Uncommitted changes roll back on every error.

    def _get(self, db, owner):
        if db is None:
            return None
        row = db.execute("SELECT data FROM profiles WHERE owner=?", (owner,)).fetchone()
        if row and len(row[0]) > 100_000:
            raise TasteError("corrupt_profile")
        return validate_profile(json.loads(row[0])) if row else None

    def read(self, owner):
        with self.transaction() as db:
            return self._get(db, owner)

    def _save(self, db, owner, profile):
        validate_profile(profile)
        db.execute("INSERT OR REPLACE INTO profiles VALUES (?, ?)", (owner, json.dumps(profile)))

    def control(self, owner, action, item_id=None, polarity=None):
        with self.transaction(create=action == "enable") as db:
            # Delete works even if this owner's payload is corrupt, without reading others.
            if action == "delete":
                if db is not None:
                    db.execute("DELETE FROM profiles WHERE owner=?", (owner,))
                    if db.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='onboarding'"
                    ).fetchone():
                        db.execute("DELETE FROM onboarding WHERE owner=?", (owner,))
                    if db.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='companions'"
                    ).fetchone():
                        db.execute("DELETE FROM companions WHERE owner=?", (owner,))
                    if db.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='locales'"
                    ).fetchone():
                        db.execute("DELETE FROM locales WHERE owner=?", (owner,))
                    if db.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_memory'"
                    ).fetchone():
                        db.execute("DELETE FROM source_memory WHERE owner=?", (owner,))
                return {
                    "deleted": True,
                    "note": "Hermes transcripts and external backups are separate.",
                }
            profile = self._get(db, owner)
            if profile is None:
                if action != "enable":
                    raise TasteError("storage_not_enabled")
                if db.execute("SELECT count(*) FROM profiles").fetchone()[0] >= 100:
                    raise TasteError("store_full")
                profile = {"version": 1, "revision": 0, "enabled": True, "prefs": []}
            before = json.loads(json.dumps(profile))
            if action in ("enable", "pause"):
                if profile["revision"] > 0 and profile["enabled"] == (action == "enable"):
                    return {"before": before, "after": profile}
                profile["enabled"] = action == "enable"
            else:
                target = next((p for p in profile["prefs"] if p["id"] == item_id), None)
                if target is None:
                    raise TasteError("preference_not_found")
                if action == "remove":
                    profile["prefs"].remove(target)
                elif action in ("confirm", "correct"):
                    if action == "confirm":
                        target["scope"] = "durable"
                    else:
                        if type(polarity) is not int or polarity not in (-1, 0, 1):
                            raise TasteError("invalid_polarity")
                        target["polarity"] = polarity
                    target["confidence"] = "user_confirmed"
                    target["provenance"] = "correction"
                    target["id"] = identifier(target)
                    target["updated_at"] = datetime.now(timezone.utc).isoformat()
                    if sum(p["id"] == target["id"] for p in profile["prefs"]) != 1:
                        raise TasteError("preference_conflict")
                else:
                    raise TasteError("invalid_action")
            profile["revision"] += 1
            self._save(db, owner, profile)
            return {"before": before, "after": profile}

    def feedback(self, owner, changes, provenance, expected_revision):
        if not isinstance(changes, list) or not 1 <= len(changes) <= 8:
            raise TasteError("invalid_preferences")
        if provenance not in ("feedback", "explicit", "onboarding"):
            raise TasteError("invalid_provenance")
        prepared = [preference(item) for item in changes]
        identities = [
            identifier(dict(item, scope="tentative"))
            if item["scope"] == "durable"
            else identifier(item)
            for item in prepared
        ]
        if len(set(identities)) != len(identities):
            raise TasteError("duplicate_preferences")
        with self.transaction() as db:
            profile = self._get(db, owner)
            if profile is None or not profile["enabled"]:
                raise TasteError("storage_not_enabled")
            if type(expected_revision) is not int or expected_revision != profile["revision"]:
                raise TasteError("profile_changed")
            added, changed, held, rejected = [], [], [], []
            for item in prepared:
                if item["scope"] == "durable":
                    item["scope"] = "tentative"
                    rejected.append("Durable promotion needs your /spoon confirm <id> command.")
                item.update(
                    id=identifier(item),
                    confidence="reported_once",
                    provenance=provenance,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
                previous = next((p for p in profile["prefs"] if p["id"] == item["id"]), None)
                if previous and previous["confidence"] == "user_confirmed":
                    rejected.append(
                        "A confirmed preference requires your direct correction command."
                    )
                    continue
                if previous:
                    changed.append({"before": dict(previous), "after": item})
                    profile["prefs"][profile["prefs"].index(previous)] = item
                else:
                    profile["prefs"].append(item)
                    added.append(item)
                if item["scope"] == "situational":
                    held.append(item["id"])
            if len(profile["prefs"]) > MAX_PREFS:
                raise TasteError("profile_full")
            profile["revision"] += 1
            self._save(db, owner, profile)
            return {
                "revision": profile["revision"],
                "added": added,
                "changed": changed,
                "held_situational": held,
                "rejected_inferences": rejected,
            }

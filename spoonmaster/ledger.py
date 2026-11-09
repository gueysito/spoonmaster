"""Conversation-scoped, expiring search snapshots and reject ledgers; never disk storage."""

import copy
import re
import secrets
import threading
import time

TTL_SECONDS = 30 * 60
MAX_SESSIONS = 100


def session_key(value):
    # This value comes only from host-injected kwargs, never model tool arguments.
    if not isinstance(value, str) or not 1 <= len(value) <= 256:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    return value


class LedgerStore:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.records = {}
        self.lock = threading.Lock()

    def _prune(self):
        for key in list(self.records):
            if self.clock() - self.records[key]["stored_at"] >= TTL_SECONDS:
                del self.records[key]

    def remember(self, session, result, origin):
        if session_key(session) is None:
            return None
        with self.lock:
            self._prune()
            identifier = secrets.token_hex(12)
            self.records.pop(session, None)
            self.records[session] = {
                "search_id": identifier,
                "stored_at": self.clock(),
                "search": {
                    "latitude": origin["latitude"],
                    "longitude": origin["longitude"],
                    "radius_m": origin.get("radius_m", 1600),
                    "candidates_in_radius": result["candidates_in_radius"],
                },
                "venues": copy.deepcopy(result["candidates"]),
                "ledger": None,
                "revision": 0,
                "presentation": None,
            }
            while len(self.records) > MAX_SESSIONS:
                self.records.pop(next(iter(self.records)))
            return identifier

    def search(self, session, identifier):
        with self.lock:
            self._prune()
            record = self.records.get(session) if session_key(session) else None
            if not record or record["search_id"] != identifier:
                return None
            return copy.deepcopy(record)

    def save(
        self,
        session,
        identifier,
        ledger,
        *,
        expected_revision=None,
        presentation=None,
        taste_scope=None,
        taste_revision=None,
    ):
        with self.lock:
            self._prune()
            record = self.records.get(session) if session_key(session) else None
            if not record or record["search_id"] != identifier:
                return False
            if expected_revision is not None and record["revision"] != expected_revision:
                return False
            record["ledger"] = copy.deepcopy(ledger)
            record["revision"] += 1
            record["presentation"] = copy.deepcopy(presentation)
            record["taste_scope"] = taste_scope
            record["taste_revision"] = taste_revision
            return True

    def current(self, session):
        with self.lock:
            self._prune()
            return copy.deepcopy(self.records.get(session)) if session_key(session) else None

    def clear_taste(self, scope, sessions=()):
        with self.lock:
            self._prune()
            for session, record in self.records.items():
                if session in sessions or (scope and record.get("taste_scope") == scope):
                    record.update(
                        ledger=None, presentation=None, taste_scope=None, taste_revision=None
                    )
                    record["revision"] += 1

    def latest(self, session):
        with self.lock:
            self._prune()
            record = self.records.get(session) if session_key(session) else None
            return copy.deepcopy(record["ledger"]) if record else None

    def forget(self, session):
        if session_key(session):
            with self.lock:
                self.records.pop(session, None)


def render_ledger(ledger, page=1):
    """Plain text is portable; paginate so a complete ledger is never silently clipped."""
    entries = ledger["entries"]
    pages = max(1, (len(entries) + 2) // 3)
    if page > pages:
        return f"That page does not exist. Use /why 1 through /why {pages}."
    lines = [
        ledger["summary"],
        f"Page {page}/{pages}; all results are as of {ledger['created_at']}.",
    ]
    if ledger["not_evaluated"]:
        lines.append(f"{ledger['not_evaluated']} other discovered venues were not evaluated.")
    for entry in entries[(page - 1) * 3 : page * 3]:
        # Names remain data, not formatting or instructions; no control chars or markdown syntax.
        name = re.sub(r"[\x00-\x1f\x7f\[\]()`*_<>]", "", entry["name"] or "Unnamed venue")[:100]
        lines.append(f"\n{name} ({entry['venue_id']}): {entry['disposition']}")
        for check in entry["checks"]:
            if check["result"] != "pass":
                lines.append(f"  {check['gate']}: {check['result']} - {check['reason']}")
    if page < pages:
        lines.append(f"Next: /why {page + 1}")
    lines.append("Full check details and source links: ask for spoon_ledger.")
    return "\n".join(lines)


def ledger_page(ledger, page=1):
    """One complete entry per tool response bounds source-heavy output without dropping checks."""
    total = max(1, len(ledger["entries"]))
    if page > total:
        return {"error": "invalid_page", "pages": total}
    return {
        **ledger,
        "entries": ledger["entries"][page - 1 : page],
        "page": page,
        "pages": total,
        "next_page": page + 1 if page < total else None,
        "note": "All candidates were evaluated. Read subsequent pages for remaining full checks.",
    }

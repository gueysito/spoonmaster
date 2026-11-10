"""One bounded dining transaction owns discovery, fallback, ranking, ledger and delivery."""

import copy
import json
import threading
import time

from . import plugin
from .cards import plain
from .discovery import validate_origin
from .ledger import LedgerStore, session_key
from .locales import place
from .outing import LOCATION_PROMPT, broad_origin
from .taste import TasteError, text

DINE_SCHEMA = {
    "name": "spoon_dine",
    "description": (
        "PRIMARY action for every dining request. Runs discovery, requested-food matching, "
        "bounded web recovery when needed, review research, hours checks, three distinct "
        "options and the /why ledger in one call. Use the user's stated/pinned origin, "
        "public area/landmark, city, country and requested food. Omit expected_arrival for now. "
        "Never substitute an ad hoc web-only recommendation. Relay all returned text/options, "
        "including empty slots and uncertainty; if delivered=true cards are already visible. "
        "No separate locale scout/approval is required to find food in a new city. "
        "Fallback sends public area, food, city and candidate venue names to host search, "
        "source excerpts to the host model, and public venue names/city to Photon geocoding. "
        "Do not put health, taste profiles, home addresses or private identifiers in area/meal."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **{
                k: v
                for k, v in plugin.RECOMMEND_SCHEMA["parameters"]["properties"].items()
                if k != "search_id"
            },
            **{
                k: v
                for k, v in plugin.CANDIDATES_SCHEMA["parameters"]["properties"].items()
                if k != "limit"
            },
            "area": {
                "type": "string",
                "maxLength": 120,
                "description": "User-stated neighborhood or public landmark only. "
                "No city-center guesses, explanatory sentences or position disclaimers.",
            },
        },
        "required": [
            "latitude",
            "longitude",
            "origin_confirmed",
            "meal",
            "area",
            "city",
            "country_code",
        ],
        "additionalProperties": False,
    },
}


class Dining:
    def __init__(self, store, taste, reviews, recovery, post=None):
        self.store, self.taste, self.reviews = store, taste, reviews
        self.recovery, self.post = recovery, post
        self.lock = threading.Lock()
        self.cache = {}

    def forget(self, session_id=None, **kwargs):
        self.cache.pop(session_id, None)

    def tool(self, args, **kwargs):
        if not isinstance(args, dict) or set(args) - set(DINE_SCHEMA["parameters"]["properties"]):
            return json.dumps({"error": "invalid_arguments"})
        if "latitude" not in args or "longitude" not in args or not args.get("origin_confirmed"):
            return json.dumps({"error": "location_required", "text": LOCATION_PROMPT})
        session = session_key(kwargs.get("session_id"))
        if session is None:
            return json.dumps({"error": "conversation_context_required"})
        try:
            validate_origin(args["latitude"], args["longitude"], args.get("radius_m", 1600))
            place(args.get("country_code"), args.get("city"))
            if not text(args.get("area"), 120) or not text(args.get("meal"), 80):
                raise ValueError
            if broad_origin(args["area"], args["city"]):
                return json.dumps(
                    {
                        "error": "location_required",
                        "text": "Which neighborhood or nearby landmark should I use? "
                        "A city alone is too broad for a nearby search.",
                    }
                )
            options = {
                k: v
                for k, v in args.items()
                if k in plugin.RECOMMEND_SCHEMA["parameters"]["properties"]
            }
            if not plugin._recommend_arguments({**options, "search_id": "0" * 24}):
                raise ValueError
        except (ValueError, TasteError):
            return json.dumps({"error": "invalid_arguments"})
        if not self.lock.acquire(blocking=False):
            return json.dumps(
                {"error": "dining_in_progress", "text": "A dining search is still running."}
            )
        try:
            for old_session in list(self.cache):
                entry = self.cache.get(old_session)
                if entry and time.monotonic() - entry["time"] >= 60:
                    self.cache.pop(old_session, None)
            key = json.dumps(args, sort_keys=True)
            cached = self.cache.get(session)
            if cached and cached["key"] == key and time.monotonic() - cached["time"] < 60:
                if self.taste is not None:
                    self.taste.guard_ledger(session)
                record = self.store.search(session, cached["search_id"])
                if record and self.taste is not None:
                    try:
                        profile = self.taste.read(session)
                        revision = profile["revision"] if profile else None
                        if revision != (record.get("presentation") or {}).get("taste_revision"):
                            record = None
                    except TasteError:
                        record = None
                if record and record["revision"] == cached["revision"] and record.get("ledger"):
                    result = copy.deepcopy(cached["result"])
                    result["reused"] = True
                    result["instruction"] = "Do not retry or repost. Use this saved explanation."
                    return json.dumps(result, ensure_ascii=False)
            raw = self._run(args, options, session)
            result = json.loads(raw)
            record = self.store.current(session)
            if result.get("search_id") and record and record.get("ledger"):
                self.cache[session] = {
                    "key": key,
                    "time": time.monotonic(),
                    "search_id": record["search_id"],
                    "revision": record["revision"],
                    "result": result,
                }
                while len(self.cache) > 100:
                    self.cache.pop(next(iter(self.cache)))
            return raw
        finally:
            self.lock.release()

    def _run(self, args, options, session):
        origin = {k: args[k] for k in ("latitude", "longitude", "radius_m") if k in args}
        identifier = self.store.remember(
            session, {"candidates": [], "candidates_in_radius": 0}, origin
        )
        found = json.loads(
            plugin.candidates(
                {**origin, "limit": 20, "meal": args["meal"]},
                _ledger_store=LedgerStore(),
                session_id=session,
            )
        )
        venues = found.get("candidates", [])
        unexamined = max(0, found.get("candidates_in_radius", len(venues)) - len(venues))
        failures = [found["error"]] if found.get("error") else []
        # Enrich even a populated OSM result: broad cuisine tags can omit relevant places.
        # The same bounded path also recovers outages; never retry Overpass here.
        if self.recovery is not None:
            extra, gaps = self.recovery.discover(args, seed=bool(found.get("error")))
            failures.extend(gaps)
            by_id = {v["venue_id"]: v for v in venues}
            for v in extra:
                prior = by_id.get(v["venue_id"])
                if prior:
                    prior.update({k: v[k] for k in ("meal_evidence", "discovery_evidence")})
                else:
                    by_id[v["venue_id"]] = v
            venues = list(by_id.values())
        # Keep evaluated accounting honest even when all sources fail.
        result = {"candidates": venues, "candidates_in_radius": len(venues) + unexamined}
        if not self.store.replace_candidates(session, identifier, result):
            return json.dumps(
                {"error": "outing_changed", "text": "This outing changed; discarded old results."}
            )
        plugin.verifier.remember(venues)
        ranked = json.loads(
            plugin.recommend_candidates(
                {**options, "search_id": identifier},
                _ledger_store=self.store,
                _taste_service=self.taste,
                _review_service=self.reviews,
                session_id=session,
            )
        )
        ranked["discovery_gaps"] = failures
        trace = getattr(self.recovery, "trace", None)
        if isinstance(trace, dict):
            ranked["discovery_research"] = trace
        record = self.store.search(session, identifier)
        if not record or not record.get("ledger"):
            return json.dumps(
                {
                    "error": "outing_changed_or_incomplete",
                    "text": "No recommendation was saved. Please start the dining search again.",
                }
            )
        record["ledger"]["discovery_gaps"] = failures
        if isinstance(trace, dict):
            record["ledger"]["discovery_research"] = trace
        if not self.store.save(
            session,
            identifier,
            record["ledger"],
            expected_revision=record["revision"],
            presentation=record.get("presentation"),
            taste_scope=record.get("taste_scope"),
            taste_revision=record.get("taste_revision"),
        ):
            return json.dumps({"error": "outing_changed"})
        ranked["text"] = presentation(ranked, args)
        # Public current-session API; no chat IDs, callbacks to strangers or gateway injection.
        ranked["delivered"] = False
        if self.store.search(session, identifier) is None:
            return json.dumps({"error": "outing_changed"})
        if self.post:
            try:
                chunks = message_chunks(ranked["text"])
                delivered = 0
                for chunk in chunks:
                    handle = self.post(chunk)
                    if not getattr(handle, "ok", False):
                        break
                    delivered += 1
                ranked["delivered"] = bool(chunks) and delivered == len(chunks)
                if delivered and not ranked["delivered"]:
                    ranked["text"] = "\n\n".join(chunks[delivered:])
            except (RuntimeError, ValueError, TypeError):
                pass  # Canonical text remains available for the host's portable final reply.
        ranked["instruction"] = (
            "Cards are already posted. Do not repeat or replace them; offer a short follow-up."
            if ranked["delivered"]
            else "Display text verbatim, including every option and empty slot."
        )
        return json.dumps(ranked, ensure_ascii=False)


def presentation(result, request):
    lines = [f"{plain(request['meal'])} near {plain(request['area'])}, {plain(request['city'])}"]
    if result.get("discovery_gaps"):
        lines.append("Some discovery sources were unavailable or incomplete; evidence gaps remain.")
        reasons = {
            "source_http_error": "The map discovery service returned an HTTP error.",
            "source_unavailable": "The map discovery service did not respond successfully.",
            "source_timeout": "The map discovery service timed out.",
            "query_cooldown": "Map discovery is cooling down; it was not retried.",
            "no_additional_grounded_mapped_matches": (
                "Web research found no additional food-matched, mapped venue inside the radius."
            ),
            "no_usable_search_excerpts": "Web results lacked usable evidence excerpts.",
        }
        lines.extend(reasons[code] for code in result["discovery_gaps"] if code in reasons)
    for card in result.get("cards", []):
        lines += ["", card["text"]]
    for role in result.get("empty_slots", []):
        lines.append(f"{role.replace('_', ' ').title()}: no additional distinct, supported match.")
    if not result.get("cards"):
        lines.append(
            "I couldn't verify nearby options from the available sources. "
            "This does not mean there are no restaurants nearby."
            if any(code.startswith("source_") for code in result.get("discovery_gaps", []))
            else "No supported shortlist within this radius. I can widen the radius if you ask."
        )
    if result.get("error"):
        lines.append("Check unavailable: " + result["error"])
    lines.append("/why explains evaluated options and gaps. Missing venues were not evaluated.")
    lines.append("Map data: © OpenStreetMap contributors, ODbL. Distances are straight-line.")
    lines.append("Opening Directions shares the search origin and venue with Google.")
    return "\n".join(lines)


def message_chunks(text):
    chunks, current = [], ""
    for line in text.splitlines():
        if len(line) > 3500:
            return []  # Preserve long source URLs for the host fallback, never break a link.
        if len(current) + len(line) + 1 > 3500:
            chunks.append(current)
            current = ""
        current += ("\n" if current else "") + line
    if current:
        chunks.append(current)
    return chunks

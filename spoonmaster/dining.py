"""One bounded dining transaction owns discovery, fallback, ranking, ledger and delivery."""

import json
import threading

from . import plugin
from .cards import plain
from .discovery import validate_origin
from .ledger import LedgerStore, session_key
from .locales import place
from .outing import LOCATION_PROMPT
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
            "area": {"type": "string", "maxLength": 120},
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
            return self._run(args, options, session)
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
            extra, gaps = self.recovery.discover(args)
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
        record = self.store.search(session, identifier)
        if not record or not record.get("ledger"):
            return json.dumps(
                {
                    "error": "outing_changed_or_incomplete",
                    "text": "No recommendation was saved. Please start the dining search again.",
                }
            )
        record["ledger"]["discovery_gaps"] = failures
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
    for card in result.get("cards", []):
        lines += ["", card["text"]]
    for role in result.get("empty_slots", []):
        lines.append(f"{role.replace('_', ' ').title()}: no additional distinct, supported match.")
    if not result.get("cards"):
        lines.append(
            "No supported shortlist within this radius. I can widen the radius if you ask."
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

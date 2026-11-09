"""Bounded verification before presentation; no fabricated fit, prices or ETA."""

import copy
from datetime import datetime, timezone

from .cards import ROLES, card_text, render_card
from .gates import arrival_gate, build_ledger, fresh
from .shortlist import admissible, shortlist
from .taste_rank import apply_taste, taste_matches


def recommend(record, request, verifier, *, now=None, profile=None):
    live_clock = now is None
    now = now or datetime.now(timezone.utc)
    venues, search = record["venues"], record["search"]
    evidence = verifier.snapshot(venues)
    ledger = build_ledger(venues, search, evidence, request, now=now)
    taste = taste_matches(venues, profile, request.get("taste_context", {}))
    apply_taste(ledger, taste, venues)
    slots = shortlist(venues, search, ledger, taste)
    if request.get("mode") == "price_tiers":
        return (
            {
                "cards": [],
                "empty_slots": ["cheap", "mid", "splurge"],
                "reason": "No sourced per-person prices; price tiers cannot be assigned.",
            },
            ledger,
            None,
        )
    if slots:
        result = verifier.verify(
            [v["venue_id"] for v in slots.values()], "finalists", request.get("country_code")
        )
        if "error" in result:
            return result, None, None
        if live_clock:
            now = datetime.now(timezone.utc)
        evidence = verifier.snapshot(venues)
        # A concurrently changed public record must not lend evidence to this search.
        if any(v["venue_id"] not in evidence for v in slots.values()):
            return {"error": "venue_evidence_changed", "action": "Run a new search."}, None, None
        ledger = build_ledger(venues, search, evidence, request, now=now)
        apply_taste(ledger, taste, venues)
    entries = {e["venue_id"]: e for e in ledger["entries"]}
    cards = [
        render_card(
            venue,
            search,
            entries[venue["venue_id"]],
            evidence.get(venue["venue_id"]),
            role=role,
            now=now,
            mode=request.get("travel_mode"),
            home_currency=request.get("home_currency"),
        )
        for role, venue in slots.items()
        if admissible(entries[venue["venue_id"]])
    ]
    for card in cards:
        matched = taste.get(card["venue_id"])
        if matched:
            card["fit"] = (
                "; ".join(matched["reasons"]) + ". Based on listed cuisine/venue identity."
            )
            card["text"] = card_text(card)
        elif taste:
            card["fit"] = "Distance is the fallback; no supported taste match for this venue."
            card["text"] = card_text(card)
    roles = {card["role"] for card in cards}
    ledger["summary"] = ledger["summary"].replace(
        "No recommendations selected yet.",
        f"Presented {len(cards)} provisional options; unknown checks remain unresolved.",
    )
    presentation = {
        "venue_ids": [card["venue_id"] for card in cards],
        "options": {
            key: request[key]
            for key in (
                "expected_arrival",
                "venue_timezone",
                "country_code",
                "travel_mode",
                "home_currency",
            )
            if key in request
        },
    }
    return (
        {
            "cards": cards,
            "empty_slots": [role for role in ROLES if role not in roles],
            "tradeoff": (
                "Supported taste matches first, then distance; cuisine variety for the wildcard."
                if taste
                else "Distance first; no supported taste matches for this search."
            ),
            "note": "Empty slots had no qualifying distinct option after bounded verification.",
            "map_privacy": "Opening directions shares origin and destination with Google.",
        },
        ledger,
        presentation,
    )


def select(record, venue_id, verifier, *, now=None):
    live_clock = now is None
    now = now or datetime.now(timezone.utc)
    presented = record.get("presentation")
    ledger = record.get("ledger")
    if not presented or venue_id not in presented["venue_ids"]:
        return {"error": "venue_not_presented"}, None, None
    if not ledger or not fresh(ledger["created_at"], now):
        return {"error": "outing_stale", "action": "Reconfirm and recommend again."}, None, None
    venue = next(v for v in record["venues"] if v["venue_id"] == venue_id)
    options = presented["options"]
    result = verifier.verify([venue_id], "selected", options.get("country_code"))
    if "error" in result:
        return result, None, None
    if live_clock:
        now = datetime.now(timezone.utc)
    if not fresh(ledger["created_at"], now):
        return {"error": "outing_stale", "action": "Reconfirm and recommend again."}, None, None
    evidence = verifier.snapshot([venue]).get(venue_id)
    if evidence is None:
        return {"error": "venue_evidence_changed", "action": "Run a new search."}, None, None
    ledger = copy.deepcopy(ledger)
    entry = next(e for e in ledger["entries"] if e["venue_id"] == venue_id)
    entry["checks"] = [
        arrival_gate(evidence, options, now) if c["gate"] == "open_at_arrival" else c
        for c in entry["checks"]
    ]
    # Preserve original outing evaluation age; refreshing hours does not reconfirm constraints.
    card = render_card(
        venue,
        record["search"],
        entry,
        evidence,
        role="selected",
        now=now,
        mode=options.get("travel_mode"),
        home_currency=options.get("home_currency"),
    )
    if not admissible(entry):
        card["caveat"] = (
            "Published schedule predicts closure. Choose another venue. " + card["caveat"]
        )
        card["text"] = card_text(card)
    return {"card": card, "proceed": admissible(entry)}, ledger, presented

"""Deterministic dining checks. Unknown facts are never silently promoted to passes."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .discovery import distance_m
from .hours import DAYS
from .verification import FRESH_SECONDS

GATES = (
    "origin",
    "radius",
    "open_at_arrival",
    "last_order",
    "travel",
    "diet_and_vetoes",
    "household",
    "taste",
    "friction",
    "evidence",
)


def verdict(gate, result, reason, sources=(), **details):
    return {"gate": gate, "result": result, "reason": reason, "sources": list(sources), **details}


def timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.utcoffset() is not None else None
    except ValueError:
        return None


def fresh(value, now):
    parsed = timestamp(value)
    return parsed is not None and 0 <= (now - parsed).total_seconds() <= FRESH_SECONDS


def weekly_at(weekly, arrival, zone):
    """Evaluate both local calendar days for overnight spill; close is exclusive."""
    local = arrival.astimezone(zone)
    minutes = local.hour * 60 + local.minute + local.second / 60
    today = DAYS[local.weekday()]
    yesterday = DAYS[(local.weekday() - 1) % 7]
    for start, end in weekly.get(today, []):
        if start <= minutes < end:
            return "pass"
    for start, end in weekly.get(yesterday, []):
        if start <= minutes + 1440 < end:
            return "pass"
    # An unspecified preceding day might contain an overnight interval.
    if today not in weekly or yesterday not in weekly:
        return "unknown"
    return "fail"


def arrival_gate(verification, request, now):
    gate = "open_at_arrival"
    if not verification:
        return verdict(gate, "unknown", "Hours verification has not been attempted.")
    sources = [e["source_url"] for e in verification["evidence"]]
    if verification["status"] != "confirmed":
        return verdict(
            gate, "unknown", "Published hours are missing, conflicting or unconfirmed.", sources
        )
    if not fresh(verification["checked_at"], now):
        return verdict(
            gate, "unknown", "Hours verification is stale or has an invalid timestamp.", sources
        )
    arrival = timestamp(request.get("expected_arrival"))
    if arrival is None or not now <= arrival <= now + timedelta(days=1):
        return verdict(gate, "unknown", "A future arrival within 24 hours is needed.", sources)
    try:
        zone = ZoneInfo(request.get("venue_timezone") or "")
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return verdict(gate, "unknown", "The venue's IANA time zone is not established.", sources)
    schedules = [
        s["parsed"]["weekly"]
        for e in verification["evidence"]
        if e["kind"] == "venue_page"
        for s in e.get("schedules", [])
        if s["parsed"]["status"] == "parsed_weekly"
    ]
    if not schedules:
        return verdict(
            gate, "unknown", "No usable venue schedule supports an arrival check.", sources
        )
    weekly_result = weekly_at(schedules[0], arrival, zone)
    # The adapter verifies published weekly hours, not date-specific closures or kitchen service.
    # Expose useful schedule math without upgrading that limited evidence to actual availability.
    return verdict(
        gate,
        "unknown",
        "Weekly schedule checked; date-specific availability is unverified.",
        sources,
        weekly_schedule_result=weekly_result,
        expected_arrival=arrival.astimezone(zone).isoformat(),
        basis="user_supplied_arrival_and_timezone",
    )


def evaluate(venue, search, verification, request, now):
    source = [venue["source_url"]]
    origin = verdict(
        "origin",
        "pass" if request.get("origin_confirmed") else "unknown",
        "User confirmed this search origin for this outing."
        if request.get("origin_confirmed")
        else "Confirm the search origin is current.",
    )
    distance = distance_m(
        search["latitude"], search["longitude"], venue["latitude"], venue["longitude"]
    )
    if venue["coordinate_basis"] != "mapped_point":
        radius = verdict(
            "radius",
            "unknown",
            "Bounding-box center is not an exact venue entrance.",
            source,
            distance_m=round(distance, 1),
        )
    else:
        inside = distance <= search["radius_m"]
        radius = verdict(
            "radius",
            "pass" if inside else "fail",
            "Mapped point is within the requested radius."
            if inside
            else "Mapped point is outside the requested radius.",
            source,
            distance_m=round(distance, 1),
        )
    excluded = request.get("excluded_venue_ids", [])
    if venue["venue_id"] in excluded:
        diet = verdict("diet_and_vetoes", "fail", "User explicitly excluded this venue.")
    elif request.get("dietary_restrictions") == []:
        diet = verdict(
            "diet_and_vetoes",
            "pass",
            "No dietary restrictions were stated for this outing; "
            "no explicit venue exclusion matches.",
        )
    else:
        diet = verdict(
            "diet_and_vetoes",
            "unknown",
            "Dietary suitability is unverified; confirm with the venue.",
            source,
        )
    evidence = verdict(
        "evidence",
        "pass" if fresh(venue.get("retrieved_at"), now) else "unknown",
        "Fresh OSM identity evidence; this does not verify other venue claims."
        if fresh(venue.get("retrieved_at"), now)
        else "Discovery evidence is missing a fresh retrieval timestamp.",
        source,
    )
    checks = [
        origin,
        radius,
        arrival_gate(verification, request, now),
        verdict("last_order", "unknown", "Kitchen last-order time has not been verified.", source),
        verdict(
            "travel",
            "unknown",
            "No route or travel-time evidence is available; distance is not ETA.",
        ),
        diet,
        verdict(
            "household", "unknown", "Household constraints and venue fit are not evaluated yet."
        ),
        verdict("taste", "unknown", "No supported taste match is attached to this evaluation."),
        verdict(
            "friction",
            "unknown",
            "Queue, reservation and payment restrictions are unverified.",
            source,
        ),
        evidence,
    ]
    failed = [check["gate"] for check in checks if check["result"] == "fail"]
    unknown = [check["gate"] for check in checks if check["result"] == "unknown"]
    return {
        "venue_id": venue["venue_id"],
        "name": venue["name"],
        "checks": checks,
        "disposition": "excluded" if failed else "unresolved" if unknown else "eligible",
        "failed_gates": failed,
        "unknown_gates": unknown,
    }


def build_ledger(venues, search, verifications, request, *, now=None):
    now = now or datetime.now(timezone.utc)
    entries = [evaluate(v, search, verifications.get(v["venue_id"]), request, now) for v in venues]
    counts = {
        kind: sum(e["disposition"] == kind for e in entries)
        for kind in ("excluded", "unresolved", "eligible")
    }
    return {
        "created_at": now.isoformat(),
        "entries": entries,
        "counts": counts,
        "evaluated": len(entries),
        "discovered_in_radius": search["candidates_in_radius"],
        "not_evaluated": search["candidates_in_radius"] - len(entries),
        "summary": (
            f"Evaluated {len(entries)} returned candidates: {counts['excluded']} excluded, "
            f"{counts['unresolved']} unresolved, {counts['eligible']} eligible. "
            "No recommendations selected yet."
        ),
    }

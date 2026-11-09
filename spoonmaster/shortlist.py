"""Conservative distance baseline; unresolved evidence stays explicitly provisional."""

import unicodedata

from .discovery import distance_m


def names(venue):
    values = [venue.get("name"), *(venue.get("alternate_names") or [])]
    return {
        "".join(c for c in unicodedata.normalize("NFKC", value).casefold() if c.isalnum())
        for value in values
        if isinstance(value, str) and value.strip()
    } - {""}


def duplicate(left, right):
    return left["venue_id"] == right["venue_id"] or (
        bool(names(left) & names(right))
        and distance_m(left["latitude"], left["longitude"], right["latitude"], right["longitude"])
        <= 50
    )


def cuisines(venue):
    return {part.strip().casefold() for part in (venue.get("cuisine") or "").split(";")} - {""}


def admissible(entry):
    checks = {check["gate"]: check for check in entry["checks"]}
    return (
        not entry["failed_gates"]
        and all(checks[key]["result"] == "pass" for key in ("origin", "radius", "evidence"))
        and checks["open_at_arrival"].get("weekly_schedule_result") != "fail"
    )


def shortlist(venues, search, ledger, taste=None):
    taste = taste or {}
    entries = {entry["venue_id"]: entry for entry in ledger["entries"]}
    ordered = sorted(
        venues,
        key=lambda v: (
            -taste.get(v["venue_id"], {}).get("score", 0),
            distance_m(search["latitude"], search["longitude"], v["latitude"], v["longitude"]),
            v["venue_id"],
        ),
    )
    unique = []
    for venue in ordered:
        # A veto on either representation must also exclude its duplicate.
        vetoed = any(
            entries[other["venue_id"]]["failed_gates"] and duplicate(venue, other)
            for other in venues
        )
        if admissible(entries[venue["venue_id"]]) and not vetoed:
            if not any(duplicate(venue, other) for other in unique):
                unique.append(venue)
    slots = dict(zip(("pick", "runner_up"), unique[:2]))
    known = set().union(*(cuisines(v) for v in unique[:2]))
    if known:
        for venue in unique[2:]:
            listed = cuisines(venue)
            if listed and listed.isdisjoint(known):
                slots["wildcard"] = venue
                break
    return slots

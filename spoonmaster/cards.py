"""Portable dining cards built from retained evidence, with explicit missing fields."""

import re
import unicodedata
from urllib.parse import urlencode

from .gates import fresh
from .phone import telephone

ROLES = ("pick", "runner_up", "wildcard")
FIELDS = (
    "name",
    "cuisine",
    "map_url",
    "directions_url",
    "hours",
    "arrival",
    "last_order",
    "closing",
    "travel",
    "cost",
    "order",
    "fit",
    "friction",
    "caveat",
    "sources",
)


def plain(value, limit=200):
    if not isinstance(value, str):
        return "Unknown"
    value = "".join(c for c in value if unicodedata.category(c) not in ("Cc", "Cf", "Zl", "Zp"))
    value = re.sub(r"[\[\]()`*_<>]", "", value).strip()
    return value[:limit] or "Unknown"


def map_links(venue, search, mode=None):
    destination = f"{venue['latitude']},{venue['longitude']}"
    origin = f"{search['latitude']},{search['longitude']}"
    directions = {"api": 1, "origin": origin, "destination": destination}
    if mode:
        directions["travelmode"] = mode
    return {
        "map_url": "https://www.google.com/maps/search/?"
        + urlencode({"api": 1, "query": destination}),
        "directions_url": "https://www.google.com/maps/dir/?" + urlencode(directions),
    }


def render_card(venue, search, entry, verification, *, role, now, mode=None, home_currency=None):
    checks = {check["gate"]: check for check in entry["checks"]}
    phone = None
    hours = "Unconfirmed"
    sources = [venue["source_url"]]
    if verification:
        for evidence in verification["evidence"]:
            url = evidence["source_url"]
            if url not in sources:
                sources.append(url)
        if verification["status"] == "conflicting":
            hours = "Conflicting published schedules"
        elif verification["status"] == "confirmed" and fresh(verification["checked_at"], now):
            published = [
                plain(schedule.get("raw"), 120)
                for evidence in verification["evidence"]
                if evidence["kind"] == "venue_page"
                for schedule in evidence.get("schedules", [])
                if schedule["parsed"]["status"] == "parsed_weekly"
            ]
            hours = (
                "Published weekly hours: "
                + "; ".join(published[:2])
                + "; date-specific availability unconfirmed"
            )
        elif not fresh(verification["checked_at"], now):
            hours = "Stale check; current hours unconfirmed"
        candidate = verification.get("phone")
        if candidate:
            # Rebuild the URI; never render a stored arbitrary link as a call action.
            phone = telephone(candidate.get("number"), candidate.get("source_url"))
            if phone:
                phone["retrieved_at"] = candidate.get("retrieved_at")
    arrival = "Unknown"
    schedule = checks["open_at_arrival"].get("weekly_schedule_result")
    if schedule:
        label = {"pass": "open", "fail": "closed", "unknown": "unknown"}[schedule]
        arrival = f"Weekly schedule predicts {label}; actual availability unconfirmed"
    cost_home = home_currency or "home currency"
    distance = checks["radius"].get("distance_m")
    fit = {
        "pick": "Nearest shortlisted option; taste fit is not established yet.",
        "runner_up": "Next nearest shortlisted alternative; taste fit is not established yet.",
        "wildcard": "A different listed cuisine; taste fit is not established yet.",
        "selected": "Your selected venue; unresolved checks still need confirmation.",
    }[role]
    matched = checks["taste"].get("matched_preferences")
    if matched:
        fit = "; ".join(matched) + ". Based on listed cuisine/venue identity."
    caveat = "Hours and other suitability checks remain unconfirmed. Call before heading there."
    if checks["diet_and_vetoes"]["result"] == "unknown":
        caveat = (
            "Dietary suitability and hours are unconfirmed. Call to confirm both before leaving."
        )
    household_warnings = [
        f"{r['rule']} ({r['strength']}): {r['reason']}"
        for gate in ("diet_and_vetoes", "household", "travel")
        for r in checks[gate].get("rules", [])
        if r["result"] != "pass"
    ]
    if household_warnings:
        caveat += " Household requirements remain unresolved; confirm them before proceeding."
    if mode == "driving":
        caveat += " Parking availability is unverified."
    if phone:
        caveat += f" [Call {phone['number']}]({phone['uri']})"
    else:
        caveat += " No sourced dialable number is available; check the venue source."
    card = {
        "role": role,
        "venue_id": venue["venue_id"],
        "status": "provisional",
        "name": plain(venue.get("name"), 100),
        "cuisine": plain(venue.get("cuisine"), 80),
        **map_links(venue, search, mode),
        "hours": hours,
        "arrival": arrival,
        "last_order": "Unknown",
        "closing": "Unknown",
        "travel": f"ETA unavailable; mode: {mode or 'unconfirmed'}",
        "cost": f"Per-person cost unknown locally; {cost_home} estimate unavailable",
        "order": "Dishes not yet verified",
        "fit": fit,
        "friction": "Queue, reservations, payment and dress code unknown",
        "caveat": caveat,
        "sources": sources,
        "phone": phone,
        "distance_m": distance,
        "unknown_checks": list(entry["unknown_gates"]),
        "household_warnings": household_warnings,
        "verification_attempted_at": verification.get("checked_at") if verification else None,
    }
    card["text"] = card_text(card)
    return card


def card_text(card):
    label = {
        "pick": "Pick",
        "runner_up": "Runner-up",
        "wildcard": "Wildcard",
        "selected": "Selected",
    }[card["role"]]
    return "\n".join(
        [
            f"{label} (provisional): {card['name']} · {card['cuisine']}",
            f"[Map]({card['map_url']}) · [Directions]({card['directions_url']})",
            f"Hours: {card['hours']}",
            f"Arrival: {card['arrival']}",
            f"Last order: {card['last_order']} · Closing: {card['closing']}",
            f"Travel: {card['travel']}",
            f"Cost: {card['cost']}",
            f"Order: {card['order']}",
            f"Why: {card['fit']}",
            f"Friction: {card['friction']}",
            *[f"Household: {warning}" for warning in card.get("household_warnings", [])],
            f"Caveat: {card['caveat']}",
            f"[Venue source]({card['sources'][0]})",
        ]
    )

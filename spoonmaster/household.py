"""Bounded outing rules and source claims. No household records are written to disk."""

import json
import re
from datetime import datetime

TRAVEL_MODES = ["walking", "driving", "transit", "bicycling"]
DIETS = ("vegetarian", "vegan", "pescetarian", "halal", "kosher", "gluten_free")
TEXT_LIST = {"type": "array", "maxItems": 20, "items": {"type": "string", "maxLength": 80}}
RULE_VALUES = {
    "highchair": {"type": "boolean", "const": True},
    "parking": {"type": "boolean", "const": True},
    "max_wait_minutes": {"type": "integer", "minimum": 0, "maximum": 240},
    "max_travel_minutes": {"type": "integer", "minimum": 0, "maximum": 240},
    "arrive_before": {"type": "string", "maxLength": 64},
}
HOUSEHOLD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["members"],
    "properties": {
        "members": {
            "type": "array",
            "maxItems": 12,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "age": {"type": "integer", "minimum": 0, "maximum": 120},
                    "dietary_restrictions": TEXT_LIST,
                    "excluded_venue_ids": TEXT_LIST,
                    "excluded_cuisines": TEXT_LIST,
                    "liked_cuisines": TEXT_LIST,
                    "disliked_cuisines": TEXT_LIST,
                },
            },
        },
        "rules": {
            "type": "array",
            "maxItems": 20,
            "items": {
                "oneOf": [
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["kind", "strength", "value"],
                        "properties": {
                            "kind": {"const": kind, "type": "string"},
                            "strength": {"type": "string", "enum": ["hard", "soft"]},
                            "value": schema,
                        },
                    }
                    for kind, schema in RULE_VALUES.items()
                ]
            },
        },
    },
}


def instant(value):
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.utcoffset() is not None else None
    except ValueError:
        return None


def text_list(values):
    return (
        isinstance(values, list)
        and len(values) <= 20
        and all(
            isinstance(v, str)
            and 1 <= len(v.strip()) <= 80
            and len(v) <= 80
            and not any(ord(c) < 32 or ord(c) == 127 for c in v)
            for v in values
        )
    )


def valid_household(value):
    if not isinstance(value, dict) or set(value) - {"members", "rules"}:
        return False
    members = value.get("members")
    if not isinstance(members, list) or len(members) > 12:
        return False
    for member in members:
        if not isinstance(member, dict) or set(member) - set(
            HOUSEHOLD_SCHEMA["properties"]["members"]["items"]["properties"]
        ):
            return False
        if "age" in member and (type(member["age"]) is not int or not 0 <= member["age"] <= 120):
            return False
        if any(not text_list(v) for k, v in member.items() if k != "age"):
            return False
    rules = value.get("rules", [])
    if not isinstance(rules, list) or len(rules) > 20:
        return False
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {"kind", "strength", "value"}:
            return False
        kind, strength, item = rule["kind"], rule["strength"], rule["value"]
        if not isinstance(kind, str) or kind not in RULE_VALUES or strength not in ("hard", "soft"):
            return False
        if kind in ("highchair", "parking") and item is not True:
            return False
        if kind.startswith("max_") and (type(item) is not int or not 0 <= item <= 240):
            return False
        if kind == "arrive_before" and instant(item) is None:
            return False
    return len(json.dumps(value)) <= 20_000


def source_claims(tags):
    """Only supported exact OSM values; source prose cannot become executable rules."""
    claims = {}
    for key in ("min_age", "max_age"):
        value = tags.get(key)
        if isinstance(value, str) and re.fullmatch(r"[0-9]{1,3}", value) and int(value) <= 120:
            claims[key] = int(value)
    if tags.get("highchair") in ("yes", "no"):
        claims["highchair"] = tags["highchair"]
    for diet in DIETS:
        value = tags.get("diet:" + diet)
        if value in ("yes", "only", "no", "limited"):
            claims["diet:" + diet] = value
    return claims


def outcome(rule, result, reason, strength="hard", sources=()):
    return {
        "rule": rule,
        "result": result,
        "reason": reason,
        "strength": strength,
        "sources": list(sources),
    }


def constraints(venue, request, fresh_source):
    """Return individual rule results without retaining ages or raw dietary text."""
    household = request.get("household", {})
    claims = venue.get("household_claims", {}) if fresh_source else {}
    source = [venue["source_url"]]
    diet_rules, family_rules, travel_rules = [], [], []
    members = household.get("members", [])
    people = [request, *members]
    listed = {part.strip().casefold() for part in (venue.get("cuisine") or "").split(";")} - {""}
    for index, person in enumerate(people):
        prefix = "outing" if index == 0 else f"member_{index}"
        if venue["venue_id"] in person.get("excluded_venue_ids", []):
            diet_rules.append(
                outcome(prefix + ".venue_veto", "fail", "User explicitly excluded this venue.")
            )
        vetoes = {v.strip().casefold() for v in person.get("excluded_cuisines", [])}
        if vetoes:
            result = "fail" if fresh_source and listed & vetoes else "unknown"
            diet_rules.append(
                outcome(
                    prefix + ".cuisine_veto",
                    result,
                    "Listed cuisine conflicts with a hard veto."
                    if result == "fail"
                    else "No confirmed cuisine-veto conflict; menu fit remains unverified.",
                    sources=source,
                )
            )
        for n, raw in enumerate(person.get("dietary_restrictions", []), 1):
            diet = raw.strip().casefold().replace(" ", "_").replace("-", "_")
            value = claims.get("diet:" + diet) if diet in DIETS else None
            diet_rules.append(
                outcome(
                    f"{prefix}.diet_{n}",
                    "fail" if value == "no" else "unknown",
                    "OSM explicitly lists no options for this dietary requirement."
                    if value == "no"
                    else "Dietary suitability needs direct venue confirmation; "
                    "tags are not a safety guarantee.",
                    sources=source,
                )
            )
        if index and "age" in person:
            age = person["age"]
            low, high = claims.get("min_age"), claims.get("max_age")
            conflict = (low is not None and age < low) or (high is not None and age > high)
            if low is not None and high is not None and low > high:
                conflict = False
            family_rules.append(
                outcome(
                    prefix + ".age",
                    "fail" if conflict else "unknown",
                    "A listed age restriction conflicts with this member."
                    if conflict
                    else "Age admission and age-appropriate seating/menu need venue confirmation.",
                    sources=source,
                )
            )
    for index, rule in enumerate(household.get("rules", []), 1):
        kind, value = rule["kind"], rule["value"]
        result, reason, sources = "unknown", "No supporting venue evidence is available.", []
        if kind == "highchair":
            if claims.get("highchair") == "no":
                result, reason = "fail", "OSM lists no highchair."
            else:
                reason = "Highchair availability needs confirmation with the venue."
            sources = source
        elif kind == "arrive_before":
            arrival = instant(request.get("expected_arrival"))
            if arrival:
                result = "pass" if arrival < instant(value) else "fail"
                reason = (
                    "User-planned arrival is "
                    + ("before" if result == "pass" else "not before")
                    + " the stated deadline; actual travel is unverified."
                )
            else:
                reason = "A user-planned arrival with UTC offset is needed for this deadline."
        elif kind == "parking":
            reason = "Parking availability is unverified; do not infer it from driving directions."
        elif kind == "max_wait_minutes":
            reason = "Queue duration is unverified against the stated wait limit."
        elif kind == "max_travel_minutes":
            reason = (
                "Route time is unverified against the stated travel limit; distance is not ETA."
            )
        target = travel_rules if kind in ("parking", "max_travel_minutes") else family_rules
        target.append(outcome(f"rule_{index}.{kind}", result, reason, rule["strength"], sources))
    return diet_rules, family_rules, travel_rules


def aggregate(gate, rules, default_reason, *, empty_pass=False):
    hard_fail = any(r["result"] == "fail" and r["strength"] == "hard" for r in rules)
    result = (
        "fail" if hard_fail else "unknown" if any(r["result"] != "pass" for r in rules) else "pass"
    )
    if not rules:
        result = "pass" if empty_pass else "unknown"
    reason = "; ".join(f"{r['rule']}: {r['reason']}" for r in rules if r["result"] != "pass")
    return {
        "gate": gate,
        "result": result,
        "reason": reason or default_reason,
        "sources": list(dict.fromkeys(s for r in rules for s in r["sources"])),
        "rules": rules,
    }

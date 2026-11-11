"""Pure outing validation and source checks; companion persistence lives separately."""

import json
from datetime import datetime

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

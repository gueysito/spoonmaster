"""Conservative weekly-hours normalization, not an open-at-arrival verdict.

OSM's full opening_hours language includes dates, holidays and rule overrides.
Only disjoint weekly rules are admitted here; everything else stays unknown.
"""

import re

DAYS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
DAY_SET = r"(?:Mo|Tu|We|Th|Fr|Sa|Su)"
DAY_EXPR = rf"{DAY_SET}(?:-{DAY_SET})?(?:,{DAY_SET}(?:-{DAY_SET})?)*"
RULE = re.compile(rf"(?:(?P<days>{DAY_EXPR}) )?(?P<times>.+)")
TIME_RANGE = re.compile(r"(\d{2}):(\d{2})-(\d{2}):(\d{2})")


def parse_weekly_hours(raw: str | None) -> dict:
    """Return structured hours only when the entire expression is understood."""
    unknown = {"status": "unknown", "reason": "missing", "weekly": None}
    if raw is None or raw == "":
        return unknown
    unknown["reason"] = "unsupported_or_ambiguous_expression"
    if not isinstance(raw, str) or len(raw) > 512:
        return unknown
    if raw == "24/7":
        return {"status": "parsed_weekly", "weekly": {day: [[0, 1440]] for day in DAYS}}

    weekly = {}
    for text in raw.split(";"):
        match = RULE.fullmatch(text.strip())
        if not match:
            return unknown
        days = _days(match["days"])
        # Overlapping rules require the full OSM override semantics. Do not guess.
        if len(days) != len(set(days)) or any(day in weekly for day in days):
            return unknown
        intervals = _intervals(match["times"])
        if intervals is None:
            return unknown
        for day in days:
            weekly[day] = intervals
    return {"status": "parsed_weekly", "weekly": weekly}


def _days(expression: str | None) -> list[str]:
    if expression is None:
        return list(DAYS)
    result = []
    for part in expression.split(","):
        edges = part.split("-")
        first, last = DAYS.index(edges[0]), DAYS.index(edges[-1])
        result.extend(DAYS[(first + offset) % 7] for offset in range((last - first) % 7 + 1))
    return result


def _intervals(expression: str) -> list[list[int]] | None:
    if expression == "off":
        return []
    result = []
    for part in expression.split(","):
        match = TIME_RANGE.fullmatch(part.strip())
        if not match:
            return None
        start_h, start_m, end_h, end_m = map(int, match.groups())
        if start_h > 23 or end_h > 24 or start_m > 59 or end_m > 59:
            return None
        if end_h == 24 and end_m != 0:
            return None
        start, end = start_h * 60 + start_m, end_h * 60 + end_m
        if start == end:
            return None
        if end < start:
            end += 1440
        result.append([start, end])
    return result

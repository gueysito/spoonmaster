"""Current meal intent stays separate from long-lived taste preferences."""

import re

ALIASES = {
    "tonkatsu": {"tonkatsu", "pork cutlet", "pork cutlets", "pork katsu"},
    "noodles": {"noodle", "noodles", "ramen", "udon", "soba", "pho", "pasta", "mein"},
    "bbq": {"bbq", "barbecue", "barbeque", "brisket", "smoked meat", "ribs"},
    "kbbq": {"kbbq", "korean bbq", "korean barbecue", "korean barbeque"},
    "hot pot": {"hot pot", "hotpot", "shabu", "sukiyaki"},
}


def words(value):
    return " ".join(re.findall(r"[^\W_]+", (value or "").casefold()))


def terms(meal):
    normalized = words(meal)
    if normalized in ("", "food", "anything", "dinner", "lunch", "breakfast", "restaurant"):
        return set()
    for key, variants in ALIASES.items():
        if normalized == key or normalized in variants:
            return variants
    return {normalized}


def matches(meal, evidence):
    wanted = terms(meal)
    haystack = " " + words(evidence) + " "
    return not wanted or any(" " + term + " " in haystack for term in wanted)


def fit(venue, meal):
    if not terms(meal):
        return {"result": "pass", "reason": "No specific cuisine requested."}
    evidence = venue.get("meal_evidence") or venue.get("cuisine")
    if not evidence:
        return {"result": "unknown", "reason": "No source establishes the requested food."}
    return {
        "result": "pass" if matches(meal, evidence) else "fail",
        "reason": "Compared requested food against listed cuisine or attributed search excerpt.",
    }

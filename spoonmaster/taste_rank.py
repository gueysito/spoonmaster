"""Match only observed venue/cuisine facts; never invent dish or dietary evidence."""

from .cards import plain
from .gates import verdict
from .shortlist import cuisines


def taste_matches(venues, profile, context):
    if not profile or not profile["enabled"]:
        return {}
    matches = {}
    for venue in venues:
        reasons, score = [], 0
        for pref in profile["prefs"]:
            if any(context.get(k) != v for k, v in pref["context"].items()):
                continue
            item = pref["item"].casefold()
            supported = (pref["kind"] == "cuisine" and item in cuisines(venue)) or (
                pref["kind"] == "venue" and item == venue["venue_id"].casefold()
            )
            if not supported or pref["polarity"] == 0:
                continue
            weight = 1 if pref["scope"] == "tentative" else 2
            score += pref["polarity"] * weight
            attitude = "like" if pref["polarity"] > 0 else "dislike"
            reasons.append(f"Your {pref['scope']} {attitude} for {plain(pref['item'], 100)}")
        if reasons:
            matches[venue["venue_id"]] = {"score": score, "reasons": reasons[:4]}
    return matches


def apply_taste(ledger, matches, venues):
    sources = {v["venue_id"]: v["source_url"] for v in venues}
    for entry in ledger["entries"]:
        matched = matches.get(entry["venue_id"])
        if not matched:
            continue
        check = verdict(
            "taste",
            "pass" if matched["score"] > 0 else "unknown",
            "; ".join(matched["reasons"]) + ". Soft ranking evidence, not dietary suitability.",
            [sources[entry["venue_id"]]],
            matched_preferences=matched["reasons"],
        )
        entry["checks"] = [check if c["gate"] == "taste" else c for c in entry["checks"]]
        entry["unknown_gates"] = [c["gate"] for c in entry["checks"] if c["result"] == "unknown"]


def companion_matches(venues, household, matches):
    """Only this outing's confirmed members contribute soft cuisine preferences."""
    for venue in venues:
        reasons, score = [], 0
        listed = cuisines(venue)
        for index, member in enumerate(household.get("members", []), 1):
            for key, polarity in (("liked_cuisines", 1), ("disliked_cuisines", -1)):
                for item in sorted(set(member.get(key, []))):
                    if item.strip().casefold() in listed:
                        score += polarity * 2
                        attitude = "likes" if polarity > 0 else "dislikes"
                        reasons.append(f"Companion {index} {attitude} {plain(item, 80)}")
        if reasons:
            previous = matches.get(venue["venue_id"], {"score": 0, "reasons": []})
            matches[venue["venue_id"]] = {
                "score": previous["score"] + score,
                "reasons": [*previous["reasons"], *reasons][:8],
            }
    return matches

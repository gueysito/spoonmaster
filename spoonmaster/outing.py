"""Current-time defaults and explicit-location guidance, without device inference."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .meal import words

LOCATION_PROMPT = (
    "Where should I look? Tell me a city and area, address, or nearby landmark, "
    "or drop a location pin if your chat app supports it."
)

# City-specific entries avoid treating multi-zone countries as a single timezone.
CITY_ZONES = {
    ("JP", "tokyo"): "Asia/Tokyo",
    ("TH", "bangkok"): "Asia/Bangkok",
    ("TH", "chiang mai"): "Asia/Bangkok",
    ("ID", "bali"): "Asia/Makassar",
    ("ID", "denpasar"): "Asia/Makassar",
    ("ID", "ubud"): "Asia/Makassar",
    ("ID", "canggu"): "Asia/Makassar",
    ("US", "new york city"): "America/New_York",
    ("US", "new york"): "America/New_York",
    ("US", "nyc"): "America/New_York",
    ("US", "san francisco"): "America/Los_Angeles",
    ("US", "sf"): "America/Los_Angeles",
    ("US", "el paso"): "America/Denver",
}


def broad_origin(area, city):
    area, city = words(area), words(city)
    return area == city or any(
        phrase in area for phrase in ("city center", "city centre", "approximate city")
    )


def location_clarification(message):
    if not isinstance(message, str):
        return None
    value = words(message)
    for prefix in ("i am in ", "i m in ", "im in "):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    if value in {city for _, city in CITY_ZONES}:
        return {
            "action": "block",
            "message": "Which neighborhood or nearby landmark should I use, and what would "
            "you like to eat? A city alone is too broad for a nearby search. "
            "You can also share a location pin if your chat app supports it.",
        }
    return None


def valid_zone(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 100:
        return False
    try:
        ZoneInfo(value)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def with_timezone(request):
    """Resolve only an established city; never the machine's timezone or location."""
    result = dict(request)
    if "venue_timezone" not in result:
        city = " ".join(result.get("city", "").casefold().split())
        zone = CITY_ZONES.get((result.get("country_code"), city))
        if zone:
            result["venue_timezone"] = zone
    return result


def dining_context(*, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "context": (
            "For restaurant recommendations ALWAYS call spoon_dine. It owns discovery, "
            "fallback, requested-food fit, reviews, all three cards and /why. Never recommend "
            "from an ad hoc web search or stop after spoon_candidates/spoon_evaluate. "
            "Use meal for the user's current food request, not their stored tastes. "
            "Do not narrow noodles to ramen or BBQ to generic restaurants. "
            "Use spoon_onboard for personalization so choices are selectable. "
            "If dining output says delivered=true, cards are already posted; do not replace "
            "them with a single pick. Otherwise relay its full text with all options. "
            f"Spoonmaster current clock (UTC): {now.astimezone(timezone.utc).isoformat()}. "
            "For dining, use the current time unless the user explicitly states another time. "
            "Omit expected_arrival for now; the plugin reads its clock on every evaluation "
            "and selected-venue recheck. Do not ask the user what time it is. "
            "Use the established destination's IANA venue_timezone, never the host timezone. "
            "Resolve an explicit local meal time against that destination and date; clarify "
            "only an ambiguous requested time. Current time is not a travel ETA. "
            "Use only an outing location stated by the user or a location pin they shared. "
            "Reuse an unambiguous location already supplied for this outing; a new city "
            "replaces the old origin. Do not infer location from IP, host, timezone, tastes "
            "or previous outings. If missing or ambiguous, ask: "
            + LOCATION_PROMPT
            + " An area/landmark is a search anchor, not a claim of exact user position. "
            "A city alone is not an origin: ask for a neighborhood or landmark; never "
            "look up a generic city-center coordinate. Keep area to the plain place name, "
            "without explanations or disclaimers. "
            "Do not request a pin on a terminal; offer the typed alternatives. "
            "Do not ask for location for unrelated questions or personalization."
        )
    }

"""Bounded host-search evidence, never direct publisher access or model verdicts."""

import json
import re
import threading
import time
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .cards import plain
from .gates import timestamp
from .locales import place, source_url
from .taste import TasteError

MAX_VENUES = 6
MAX_SOURCES = 8
MAX_AGE_DAYS = 365
CROWD_DOMAINS = {"yelp.com", "tabelog.com", "wongnai.com", "tripadvisor.com", "opentable.com"}


def words(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return " ".join(re.findall(r"[^\W_]+", value, flags=re.UNICODE))


def address_words(value):
    aliases = {
        "street": "st",
        "avenue": "ave",
        "road": "rd",
        "boulevard": "blvd",
        "north": "n",
        "south": "s",
        "east": "e",
        "west": "w",
    }
    return " ".join(aliases.get(word, word) for word in words(value).split())


def contains(haystack, needle):
    return bool(needle) and (" " + needle + " ") in (" " + haystack + " ")


def query_text(value):
    # Public venue data cannot inject search operators or control characters.
    return words(value)[:160]


def publisher_key(domain):
    """Conservatively group subdomains; do not claim corporate independence."""
    parts = domain.split(".")
    country_suffix = len(parts[-1]) == 2 and parts[-2] in {"co", "com", "org", "net", "ac"}
    return ".".join(parts[-3:] if country_suffix else parts[-2:])


def publishers(sources):
    result = []
    for source in sources[:MAX_SOURCES]:
        roles = source.get("roles", [source.get("role")])
        if not set(roles) & {"quality", "local_opinion"}:
            continue
        if source.get("access", "search_or_user_content") != "search_or_user_content":
            continue
        domains = source.get("domains")
        if domains is None and source_url(source.get("url")):
            domains = [urlsplit(source["url"]).hostname]
        for domain in domains or []:
            domain = domain.removeprefix("www.")
            if not source_url("https://" + domain):
                continue
            result.append(
                {
                    "name": plain(source["name"], 100),
                    "domain": domain,
                    "editorial": "quality" in roles and publisher_key(domain) not in CROWD_DOMAINS,
                }
            )
    return result[:MAX_SOURCES]


def branch_match(venue, title, snippet, country, city):
    """Require a title/name match or compact name/address excerpt, plus city corroboration.

    Search-query echo and a city-only name match cannot establish a branch. Fail
    closed on missing address, a different known city, or a different known country.
    """
    address = venue.get("address") or {}
    if venue.get("country_code") not in (None, country):
        return False
    if address.get("city"):
        try:
            if place(country, address["city"]) != place(country, city):
                return False
        except TasteError:
            return False
    names = [venue.get("name"), *(venue.get("alternate_names") or [])]
    number, street = address_words(address.get("housenumber")), address_words(address.get("street"))
    if not number or not street:
        return False
    for fragment in re.split(r"\.{3}|…|\n", snippet):
        content = address_words(fragment)
        address_match = contains(content, number + " " + street) or contains(
            content, street + " " + number
        )
        named = any(contains(words(title), words(name)) for name in names if name)
        local_name = any(contains(content, address_words(name)) for name in names if name)
        if address_match and (named or (local_name and len(fragment) <= 240)):
            return True
    return False


def rating_from(snippet):
    """Accept a single explicit value/scale/count expression, never guess a scale."""
    pattern = (
        r"(?<![\d.])([0-9]+(?:\.[0-9]+)?)\s*(?:/|out of)\s*"
        r"(5|10)\s*(?:stars?)?\s*[-·,:( ]*"
        r"([0-9][0-9,]*)\s*(?:reviews|ratings)\b"
    )
    matches = list(re.finditer(pattern, snippet, flags=re.IGNORECASE))
    if len(matches) != 1:
        return None
    value, scale, count = matches[0].groups()
    value, scale, count = float(value), int(scale), int(count.replace(",", ""))
    if not 0 <= value <= scale or not 1 <= count <= 100_000_000:
        return None
    return {
        "value": value,
        "scale": scale,
        "count": count,
        "basis": "Explicit rating/scale/count in search excerpt; not review-text analysis.",
    }


def parse_hit(hit, venue, sources, country, city, now):
    if not isinstance(hit, dict) or not source_url(hit.get("url")):
        return None
    title, snippet = hit.get("title"), hit.get("description")
    if not isinstance(title, str) or not isinstance(snippet, str):
        return None
    if not 1 <= len(title) <= 500 or not 1 <= len(snippet) <= 2000:
        return None
    host = urlsplit(hit["url"]).hostname.removeprefix("www.")
    source = next(
        (s for s in sources if host == s["domain"] or host.endswith("." + s["domain"])), None
    )
    if source is None or not branch_match(venue, title, snippet, country, city):
        return None
    city_key = place(country, city).split(":", 1)[1]
    city_names = {city_key}
    if country == "US":
        city_names |= {"new york", "nyc"} if city_key == "new york city" else set()
        city_names |= {"sf"} if city_key == "san francisco" else set()
    location = words(title + " " + snippet + " " + urlsplit(hit["url"]).path)
    if not any(contains(location, name) for name in city_names):
        return None
    raw_date = hit.get("publishedDate", hit.get("published_date", hit.get("date")))
    published = None
    if isinstance(raw_date, str):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
            raw_date += "T00:00:00+00:00"
        published = timestamp(raw_date)
    stale = published is not None and not 0 <= (now - published).days <= MAX_AGE_DAYS
    # Only explicit recommendation labels in a matching result title qualify.
    # Reviews/mentions alone, snippet sentiment, ratings and model claims do not.
    normalized = words(title)
    positive = bool(re.search(r"\bbest (?:\w+ ){0,4}restaurants?\b", normalized)) or any(
        contains(normalized, term)
        for term in (
            "best restaurants",
            "essential restaurants",
            "recommended restaurants",
            "bib gourmand",
            "michelin starred",
        )
    )
    negative = any(
        contains(normalized, term)
        for term in (
            "not",
            "worst",
            "closed",
            "closing",
            "formerly",
            "lost",
            "removed",
        )
    )
    support = source["editorial"] and positive and not negative and not stale
    return {
        "publisher": source["name"],
        "publisher_key": publisher_key(source["domain"]),
        "url": hit["url"],
        "title": plain(title, 300),
        "snippet": plain(snippet, 500),
        "retrieved_at": now.isoformat(),
        "published_at": published.isoformat() if published else None,
        "kind": "editorial_recommendation" if support else "review_reference",
        "rating": rating_from(snippet) if not source["editorial"] and not stale else None,
        "status": "stale_or_future" if stale else "date_unknown" if not published else "dated",
        "basis": "Search snippet; venue name and exact mapped street address matched. "
        "Not a full review, verified sentiment, current hours or safety evidence.",
    }


class ReviewSearch:
    def __init__(self, locales, clock=time.monotonic):
        self.locales = locales
        self.clock = clock
        self.lock = threading.Lock()
        self.next_search = 0

    def collect(self, venues, country, city, session):
        result = {
            "status": "unavailable",
            "venues": {},
            "attempted": 0,
            "failed_searches": 0,
            "limit": MAX_VENUES,
            "note": "Missing coverage is unknown, not a negative review. "
            "Only branch-matched search evidence can influence ranking.",
        }
        if not country or not city:
            return {**result, "status": "locale_required"}
        try:
            sources, scope = self.locales.review_sources(country, city, session)
        except TasteError as error:
            return {**result, "status": str(error)}
        sources = publishers(sources)
        if not sources:
            return {**result, "status": "no_review_sources"}
        if self.locales.dispatch is None:
            return {**result, "status": "host_search_unavailable"}
        if not venues:
            return {**result, "status": "no_admissible_candidates"}
        if not self.lock.acquire(blocking=False):
            return {**result, "status": "review_search_in_progress"}
        try:
            if self.clock() < self.next_search:
                return {**result, "status": "review_search_cooldown"}
            self.next_search = self.clock() + 60
            canonical_city = place(country, city).split(":", 1)[1]
            for venue in venues[:MAX_VENUES]:
                if not self.locales.review_scope_matches(country, city, session, scope):
                    return {**result, "venues": {}, "status": "review_context_changed"}
                name = query_text(venue.get("name"))
                address = venue.get("address") or {}
                if not name or not address.get("housenumber") or not address.get("street"):
                    continue
                query = (
                    f'"{name}" {query_text(address["housenumber"])} '
                    f"{query_text(address['street'])} {canonical_city} {country} "
                    "restaurant reviews recommendations ("
                    + " OR ".join("site:" + s["domain"] for s in sources)
                    + ")"
                )
                result["attempted"] += 1
                try:
                    raw = self.locales.dispatch("web_search", {"query": query, "limit": 5})
                    if not isinstance(raw, str) or len(raw) > 100_000:
                        raise ValueError
                    envelope = json.loads(raw)
                    if not isinstance(envelope, dict) or envelope.get("success") is not True:
                        raise ValueError
                    data = envelope.get("data")
                    if not isinstance(data, dict) or not isinstance(data.get("web"), list):
                        raise ValueError
                    found, seen = [], set()
                    now = datetime.now(timezone.utc)
                    for hit in data["web"][:5]:
                        item = parse_hit(hit, venue, sources, country, city, now)
                        if item and item["publisher_key"] not in seen:
                            found.append(item)
                            seen.add(item["publisher_key"])
                    order = {publisher_key(s["domain"]): i for i, s in enumerate(sources)}
                    found.sort(key=lambda item: order.get(item["publisher_key"], MAX_SOURCES))
                    result["venues"][venue["venue_id"]] = found
                except (ValueError, TypeError, KeyError, RuntimeError, OSError, RecursionError):
                    result["failed_searches"] += 1
            if not self.locales.review_scope_matches(country, city, session, scope):
                return {**result, "venues": {}, "status": "review_context_changed"}
            result["status"] = "partial" if result["failed_searches"] else "searched"
            return result
        finally:
            self.lock.release()


def support_count(items):
    return len({i["publisher_key"] for i in items if i["kind"] == "editorial_recommendation"})


def ranking_weights(venues, taste, research):
    """Only compare crowd scores within a taste tie and shared source/scale coverage."""
    groups, ratings, weights = {}, {}, {}
    for venue in venues:
        key = venue["venue_id"]
        groups.setdefault(taste.get(key, {}).get("score", 0), []).append(key)
        ratings[key] = {
            (item["publisher_key"], item["rating"]["scale"]): item["rating"]["value"]
            for item in research["venues"].get(key, [])
            if item.get("rating")
        }
    for keys in groups.values():
        common = set.intersection(*(set(ratings[key]) for key in keys)) if len(keys) > 1 else set()
        # Retain source-ladder/search order, never average or normalize platform scales.
        ordered = [source for source in ratings[keys[0]] if source in common]
        for key in keys:
            weights[key] = (
                support_count(research["venues"].get(key, [])),
                *(ratings[key][source] for source in ordered),
            )
    return weights


def attach_reviews(ledger, research):
    for entry in ledger["entries"]:
        entry["review_evidence"] = research["venues"].get(entry["venue_id"], [])
    ledger["review_research"] = {k: v for k, v in research.items() if k != "venues"}

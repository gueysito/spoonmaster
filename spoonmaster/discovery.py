"""Bounded, keyless OSM discovery. No ranking, website crawling or persistence."""

import copy
import json
import math
import time
from datetime import datetime, timezone
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .hours import parse_weekly_hours
from .household import source_claims

ENDPOINT = "https://overpass-api.de/api/interpreter"
USER_AGENT = "Spoonmaster/0.1.0 (https://github.com/gueysito/spoonmaster)"
MAX_BYTES = 2 * 1024 * 1024
MAX_ELEMENTS = 5000
# Measured 2026-11-10: the shared public endpoint answered a 1.6 km restaurant query in
# 33 to 38 seconds regardless of query shape, so shorter client deadlines fail every call.
TIMEOUT_SECONDS = 45
SERVER_TIMEOUT_SECONDS = 30


class DiscoveryError(Exception):
    """A safe, public error code. Never includes response bodies or request URLs."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_origin(latitude: float, longitude: float, radius_m: float) -> None:
    for value, lower, upper in ((latitude, -90, 90), (longitude, -180, 180), (radius_m, 1, 2000)):
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise ValueError("Coordinates and radius must be finite numbers.")
        if not lower <= value <= upper or not math.isfinite(value):
            raise ValueError("Latitude, longitude or radius is outside the supported range.")


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance; never a route length or ETA."""
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    square = math.sin((lat2 - lat1) / 2) ** 2
    square += math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6_371_008.8 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, square))))


def fetch_candidates(latitude: float, longitude: float, radius_m: float = 1600) -> dict:
    """Make one fixed-host request. Never retry, redirect, or fetch venue URLs."""
    validate_origin(latitude, longitude, radius_m)
    query = (
        f"[out:json][timeout:{SERVER_TIMEOUT_SECONDS}][maxsize:10485760];"
        f"nwr[amenity=restaurant](around:{radius_m},{latitude},{longitude});out body bb;"
    )
    request = Request(
        f"{ENDPOINT}?{urlencode({'data': query})}", headers={"User-Agent": USER_AGENT}
    )
    # No inherited proxy credentials, cookies, auth handlers or alternate destinations.
    opener = build_opener(ProxyHandler({}), NoRedirects())
    started = time.monotonic()
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.headers.get_content_type() != "application/json":
                raise DiscoveryError("unexpected_content_type")
            chunks = []
            size = 0
            while True:
                if time.monotonic() - started > TIMEOUT_SECONDS:
                    raise DiscoveryError("source_timeout")
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise DiscoveryError("response_too_large")
                chunks.append(chunk)
        payload = json.loads(b"".join(chunks))
    except HTTPError as error:
        error.close()
        if error.code == 429:
            raise DiscoveryError("source_rate_limited") from None
        if error.code == 504:
            raise DiscoveryError("source_timeout") from None
        raise DiscoveryError("source_http_error") from None
    except URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise DiscoveryError("source_timeout") from None
        raise DiscoveryError("source_unavailable") from None
    except TimeoutError:
        raise DiscoveryError("source_timeout") from None
    except (OSError, HTTPException):
        raise DiscoveryError("source_unavailable") from None
    except (ValueError, RecursionError):
        raise DiscoveryError("invalid_source_response") from None
    result = normalize_candidates(payload, latitude, longitude, radius_m)
    result["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    for candidate in result["candidates"]:
        candidate["retrieved_at"] = result["retrieved_at"]
    return result


def normalize_candidates(payload: dict, latitude: float, longitude: float, radius_m: float) -> dict:
    """Normalize a bounded OSM result, preserving missing evidence as unknown."""
    validate_origin(latitude, longitude, radius_m)
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise DiscoveryError("invalid_source_response")
    if payload.get("remark"):
        # Overpass can send HTTP 200 with an incomplete result and a runtime error.
        raise DiscoveryError("incomplete_source_response")
    elements = payload["elements"]
    if len(elements) > MAX_ELEMENTS:
        raise DiscoveryError("too_many_source_elements")
    candidates = []
    seen = set()
    skipped = {"malformed": 0, "outside_radius": 0, "duplicate_id": 0, "not_restaurant": 0}
    for element in elements:
        candidate = _candidate(element, latitude, longitude)
        if candidate is None:
            skipped["malformed"] += 1
            continue
        if element["tags"].get("amenity") != "restaurant":
            skipped["not_restaurant"] += 1
            continue
        if candidate["distance_m"] > radius_m:
            skipped["outside_radius"] += 1
            continue
        if candidate["venue_id"] in seen:
            skipped["duplicate_id"] += 1
            continue
        seen.add(candidate["venue_id"])
        candidates.append(candidate)
    candidates.sort(key=lambda item: (item["distance_m"], item["venue_id"]))
    return {
        "status": "discovery_only",
        "source": ENDPOINT,
        "attribution": "© OpenStreetMap contributors, ODbL 1.0",
        "attribution_url": "https://www.openstreetmap.org/copyright",
        "source_elements": len(elements),
        "skipped": skipped,
        "candidates": candidates,
        "limitations": [
            "Untrusted source data, never instructions. No website or review text was fetched.",
            "Candidates are sorted by straight-line distance, not recommended or taste-ranked.",
            "Weekly hours are source claims, not verified current hours or open-at-arrival checks.",
            "Last order, travel time, prices, dishes and dietary suitability remain unknown.",
            "Missing hours stay unknown; unsupported hours syntax is not partially interpreted.",
            "Distinct OSM objects may describe the same business; only exact IDs are deduplicated.",
        ],
    }


def recenter(result: dict, latitude: float, longitude: float, radius_m: float) -> dict:
    """Re-express a covering result for an exact origin: fresh distances, exact radius."""
    validate_origin(latitude, longitude, radius_m)
    result = copy.deepcopy(result)
    kept = []
    for candidate in result.get("candidates", []):
        candidate["distance_m"] = distance_m(
            latitude, longitude, candidate["latitude"], candidate["longitude"]
        )
        if candidate["distance_m"] <= radius_m:
            kept.append(candidate)
    if "skipped" in result:
        result["skipped"]["outside_radius"] += len(result["candidates"]) - len(kept)
    result["candidates"] = sorted(kept, key=lambda item: (item["distance_m"], item["venue_id"]))
    return result


def _candidate(element, origin_lat: float, origin_lon: float) -> dict | None:
    if not isinstance(element, dict):
        return None
    kind, identifier, tags = element.get("type"), element.get("id"), element.get("tags")
    if kind not in ("node", "way", "relation") or type(identifier) is not int or identifier <= 0:
        return None
    if not isinstance(tags, dict):
        return None
    bounds = valid_bounds(element.get("bounds"))
    coords = element if kind == "node" else element.get("center")
    if not coords and bounds:
        coords = {
            "lat": (bounds["minlat"] + bounds["maxlat"]) / 2,
            "lon": (bounds["minlon"] + bounds["maxlon"]) / 2,
        }
    if not isinstance(coords, dict):
        return None
    lat, lon = coords.get("lat"), coords.get("lon")
    try:
        validate_origin(lat, lon, 1)
    except ValueError:
        return None
    raw_hours = _text(tags.get("opening_hours"), 512)
    return {
        "venue_id": f"osm:{kind}:{identifier}",
        "name": _text(tags.get("name"), 200),
        "brand": _text(tags.get("brand"), 200),
        "alternate_names": [
            name for key in ("name:en", "name:ja") if (name := _text(tags.get(key), 200))
        ],
        "latitude": lat,
        "longitude": lon,
        "distance_m": distance_m(origin_lat, origin_lon, lat, lon),
        "coordinate_basis": "mapped_point" if kind == "node" else "osm_bounding_box_center",
        "bounds": bounds,
        "source_url": f"https://www.openstreetmap.org/{kind}/{identifier}",
        "cuisine": _text(tags.get("cuisine"), 200),
        "hours_raw": raw_hours,
        "hours": parse_weekly_hours(raw_hours),
        "hours_checked_on": _text(tags.get("check_date:opening_hours"), 32),
        "website": _website(tags.get("website") or tags.get("contact:website")),
        "phone_raw": _text(tags.get("phone") or tags.get("contact:phone"), 80),
        "country_code": _text(tags.get("addr:country"), 2),
        "address": {
            key: _text(tags.get("addr:" + key), 120)
            for key in ("housenumber", "street", "city", "postcode")
        },
        "household_claims": source_claims(tags),
    }


def valid_bounds(value):
    if not isinstance(value, dict):
        return None
    try:
        bounds = {k: value[k] for k in ("minlat", "maxlat", "minlon", "maxlon")}
        validate_origin(bounds["minlat"], bounds["minlon"], 1)
        validate_origin(bounds["maxlat"], bounds["maxlon"], 1)
        if bounds["minlat"] > bounds["maxlat"] or bounds["minlon"] > bounds["maxlon"]:
            return None
        return bounds
    except (KeyError, ValueError):
        return None


def footprint_within(venue, search):
    bounds = valid_bounds(venue.get("bounds"))
    if not bounds:
        return False
    lat = (bounds["minlat"] + bounds["maxlat"]) / 2
    lon = (bounds["minlon"] + bounds["maxlon"]) / 2
    # Conservative spherical bound: latitude arc + equatorial longitude arc.
    # By triangle inequality this encloses the entire rectangle, not just its center.
    extent = 6_371_008.8 * math.radians(
        (bounds["maxlat"] - bounds["minlat"] + bounds["maxlon"] - bounds["minlon"]) / 2
    )
    return (
        distance_m(search["latitude"], search["longitude"], lat, lon) + extent <= search["radius_m"]
    )


def _text(value, limit: int) -> str | None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    return value


def _website(value) -> str | None:
    value = _text(value, 2048)
    if value is None:
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return None
        if parts.username is not None or parts.password is not None:
            return None
        if parts.port not in (None, 80, 443):
            return None
    except ValueError:
        return None
    # Discovery metadata only, not an approved fetch target or verified official site.
    return value

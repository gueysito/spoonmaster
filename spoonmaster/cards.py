"""Portable text hygiene and optional ride-service links."""

import re
import unicodedata


def plain(value, limit=200):
    if not isinstance(value, str):
        return "Unknown"
    value = "".join(c for c in value if unicodedata.category(c) not in ("Cc", "Cf", "Zl", "Zp"))
    value = re.sub(r"[\[\]()`*_<>]", "", value).strip()
    return value[:limit] or "Unknown"


def ride_links(country, distance):
    if distance is None or distance <= 804.672:
        return []
    links = {
        "US": [("Uber", "https://m.uber.com/")],
        "JP": [("Uber", "https://m.uber.com/")],
        "TH": [("Grab", "https://www.grab.com/th/en/download/")],
        "ID": [
            ("Grab", "https://www.grab.com/id/download/"),
            ("Gojek", "https://www.gojek.com/en-id/"),
        ],
    }.get(country, [])
    if not links:
        return []
    return [
        "Ride options: " + " · ".join(f"[{name}]({url})" for name, url in links),
        "Open the service and enter the destination; no fare, pickup or booking is prefilled.",
    ]

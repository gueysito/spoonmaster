"""Render sourced telephone numbers without guessing a country or initiating calls."""

import re


def telephone(raw, source_url, country=None):
    if not isinstance(raw, str) or len(raw) > 80:
        return None
    value = raw.strip()
    if value.startswith("tel:"):
        value = value[4:]
    if not re.fullmatch(r"\+?[0-9 ()-]+", value):
        return None
    number = re.sub(r"[ ()-]", "", value)
    # Only convert a local number when the venue has an explicit country code.
    prefixes = {"JP": "81", "TH": "66", "ID": "62", "KR": "82"}
    if not number.startswith("+") and country in prefixes and number.startswith("0"):
        number = "+" + prefixes[country] + number[1:]
    if not re.fullmatch(r"\+[1-9][0-9]{6,14}", number):
        return None
    return {"number": number, "uri": "tel:" + number, "source_url": source_url}

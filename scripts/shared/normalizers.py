"""Normalization helpers for future pipeline steps."""

import re


def normalize_text(value):
    """Return a trimmed text value.

    This small helper is enough for the scaffold and can be extended later.
    """
    if value is None:
        return ""
    return str(value).strip()


def normalize_integer(value):
    """Return an integer when possible, otherwise None."""
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_year(value):
    """Extract a 4-digit year from a year text."""
    value = normalize_text(value)
    match = re.search(r"(19|20)\d{2}", value)
    if not match:
        return None
    return int(match.group(0))


def normalize_price_yen(value):
    """Convert a price text such as '323.9万円' into yen."""
    value = normalize_text(value).replace(" ", "")
    if not value:
        return None

    if "5万円以下" in value:
        return 50000

    match = re.search(r"([\d.]+)万円", value)
    if not match:
        return None

    return int(float(match.group(1)) * 10000)


def normalize_mileage_km(value):
    """Convert mileage text such as '6.6万km' or '5000km' into kilometers."""
    value = normalize_text(value).replace(" ", "")
    if not value:
        return None

    if "万km" in value:
        match = re.search(r"([\d.]+)万km", value)
        if match:
            return int(float(match.group(1)) * 10000)

    match = re.search(r"(\d[\d,]*)km", value, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", ""))

    return None


def normalize_grade(model_name, listing_title):
    """Extract a compact grade string from the listing title.

    For the first Carsensor implementation we keep this heuristic intentionally
    small and take the first few tokens after the model name.
    """
    listing_title = normalize_text(listing_title)
    model_name = normalize_text(model_name)

    if listing_title.startswith(model_name):
        tail = listing_title[len(model_name):].strip()
    else:
        tail = listing_title

    tokens = [token for token in tail.split(" ") if token]
    if not tokens:
        return ""

    return " ".join(tokens[:4]).strip()


def label_mileage_band(mileage_km, mileage_bands):
    """Return the configured mileage band label for a mileage value."""
    if mileage_km is None:
        return ""

    for band in mileage_bands:
        if band["min"] <= mileage_km < band["max"]:
            return band["label"]

    return ""


def label_price_band(price_yen, band_size_manen, max_manen):
    """Return a simple fixed-width price band label."""
    if price_yen is None:
        return ""

    price_manen = price_yen / 10000
    if price_manen >= max_manen:
        return f"{max_manen}万円以上"

    lower = int(price_manen // band_size_manen) * band_size_manen
    upper = lower + band_size_manen
    return f"{lower}万円台〜{upper}万円未満"


def parse_price_range_yen(value):
    """Parse a price range such as '127万円～199万円' into min/max yen."""
    value = normalize_text(value).replace(" ", "")
    if not value:
        return (None, None)

    if "～" not in value:
        single_value = normalize_price_yen(value)
        return (single_value, single_value)

    lower_text, upper_text = value.split("～", 1)
    return (normalize_price_yen(lower_text), normalize_price_yen(upper_text))


def normalize_mileage_band_range(value):
    """Convert mileage band text into label and approximate range.

    Examples:
    - 1万km -> (1万km, 10000, 19999)
    - 2〜3万km -> (2〜3万km, 20000, 39999)
    """
    value = normalize_text(value).replace(" ", "")
    if not value:
        return ("", None, None)

    range_match = re.match(r"(?P<lower>\d+)〜(?P<upper>\d+)万km", value)
    if range_match:
        lower = int(range_match.group("lower")) * 10000
        upper = int(range_match.group("upper")) * 10000 + 9999
        return (value, lower, upper)

    single_match = re.match(r"(?P<single>\d+)万km", value)
    if single_match:
        lower = int(single_match.group("single")) * 10000
        upper = lower + 9999
        return (value, lower, upper)

    return (value, None, None)

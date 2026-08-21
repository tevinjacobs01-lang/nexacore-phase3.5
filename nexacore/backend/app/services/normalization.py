"""
Normalization service (Sprint 12).

Pure functions, no DB access — safe to unit test directly and reuse from
both the CSV importer and any future collector's `normalize()` method.
"""
from __future__ import annotations

import re
from datetime import date, datetime

PRICE_STRIP_RE = re.compile(r"[^\d.,-]")
PHONE_STRIP_RE = re.compile(r"[^\d+]")

PROPERTY_TYPE_SYNONYMS = {
    "house": "House", "home": "House", "single family": "House",
    "apartment": "Apartment", "apt": "Apartment", "flat": "Apartment",
    "townhouse": "Townhouse", "town house": "Townhouse",
    "duplex": "Duplex",
    "plot": "Vacant Land", "vacant land": "Vacant Land", "land": "Vacant Land",
    "commercial": "Commercial",
}

PROVINCE_SYNONYMS = {
    "gauteng": "Gauteng", "gp": "Gauteng",
    "western cape": "Western Cape", "wc": "Western Cape",
    "kwazulu-natal": "KwaZulu-Natal", "kwazulu natal": "KwaZulu-Natal", "kzn": "KwaZulu-Natal",
    "eastern cape": "Eastern Cape", "ec": "Eastern Cape",
    "free state": "Free State", "fs": "Free State",
    "limpopo": "Limpopo", "mpumalanga": "Mpumalanga",
    "north west": "North West", "northern cape": "Northern Cape", "nc": "Northern Cape",
}


def normalize_price(raw: str | int | float | None) -> float | None:
    """'R 1 250 000' / 'R1,250,000.00' / 1250000 -> 1250000.0"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    cleaned = PRICE_STRIP_RE.sub("", str(raw)).strip()
    cleaned = cleaned.replace(" ", "").replace(",", "")
    if not cleaned or cleaned in ("-", "."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_phone(raw: str | None, default_country_code: str = "27") -> str | None:
    """Best-effort normalization to a consistent digits(+cc) format.
    '082 123 4567' -> '+27821234567'; leaves already-international numbers alone."""
    if not raw:
        return None
    cleaned = PHONE_STRIP_RE.sub("", str(raw))
    if not cleaned:
        return None
    if cleaned.startswith("+"):
        return cleaned
    if cleaned.startswith("0"):
        return f"+{default_country_code}{cleaned[1:]}"
    if cleaned.startswith(default_country_code):
        return f"+{cleaned}"
    return cleaned


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = str(raw).strip().lower()
    return cleaned if EMAIL_RE.match(cleaned) else None


def _titlecase_place(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = str(raw).strip()
    return " ".join(w.capitalize() for w in cleaned.split()) if cleaned else None


def normalize_suburb(raw: str | None) -> str | None:
    return _titlecase_place(raw)


def normalize_city(raw: str | None) -> str | None:
    return _titlecase_place(raw)


def normalize_province(raw: str | None) -> str | None:
    if not raw:
        return None
    key = str(raw).strip().lower()
    return PROVINCE_SYNONYMS.get(key, _titlecase_place(raw))


def normalize_property_type(raw: str | None) -> str | None:
    if not raw:
        return None
    key = str(raw).strip().lower()
    return PROPERTY_TYPE_SYNONYMS.get(key, _titlecase_place(raw))


def normalize_int_count(raw) -> int | None:
    """For bedrooms/bathrooms/garages — handles '3', '3.0', 'studio' (->0), etc."""
    if raw is None:
        return None
    if isinstance(raw, str) and raw.strip().lower() in ("studio", "bachelor"):
        return 0
    try:
        return int(float(raw))
    except (ValueError, TypeError):
        return None


def normalize_listing_date(raw) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(raw).strip(), fmt).date()
        except ValueError:
            continue
    return None


def normalize_url(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = str(raw).strip()
    if not cleaned:
        return None
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return cleaned


def validate_listing(listing) -> list[str]:
    """Basic completeness/sanity checks. `listing` can be a Listing dataclass
    or anything with matching attributes (e.g. a dict-like row)."""
    problems: list[str] = []

    def get(field):
        return listing.get(field) if isinstance(listing, dict) else getattr(listing, field, None)

    if not get("address") and not get("listing_reference"):
        problems.append("missing both address and listing_reference")

    price = get("asking_price")
    rental = get("monthly_rental")
    if price is not None and price < 0:
        problems.append("asking_price is negative")
    if rental is not None and rental < 0:
        problems.append("monthly_rental is negative")

    listing_type = get("listing_type")
    if listing_type and listing_type not in ("sale", "rent"):
        problems.append(f"unrecognized listing_type '{listing_type}'")

    email = get("email")
    if email and not EMAIL_RE.match(str(email)):
        problems.append("email is not a valid format")

    return problems

"""
Duplicate-detection engine (Sprint 13).

Classifies a candidate listing against an existing one — never deletes or
merges automatically. Persisted via DuplicateMatch for human review.

Classification (most to least confident):
- exact:    same source + same listing_url, OR same listing_reference+source
- likely:   same normalized address+suburb AND (same contact info OR same price)
- possible: same normalized address+suburb only, OR same contact info +
            similar characteristics (beds/baths/type) but different address
- unique:   none of the above
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DuplicateClassification:
    match_type: str  # exact | likely | possible | unique
    reason: str


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def classify_duplicate(candidate, existing) -> DuplicateClassification:
    """`candidate` and `existing` need: listing_source, listing_url,
    listing_reference, address, suburb, contact_number, email, asking_price,
    monthly_rental, property_type, bedrooms, bathrooms — as attributes or
    dict keys."""

    def get(obj, field):
        return obj.get(field) if isinstance(obj, dict) else getattr(obj, field, None)

    c_source, e_source = _norm(get(candidate, "listing_source")), _norm(get(existing, "listing_source"))
    c_url, e_url = _norm(get(candidate, "listing_url")), _norm(get(existing, "listing_url"))
    c_ref, e_ref = _norm(get(candidate, "listing_reference")), _norm(get(existing, "listing_reference"))
    c_addr, e_addr = _norm(get(candidate, "address")), _norm(get(existing, "address"))
    c_suburb, e_suburb = _norm(get(candidate, "suburb")), _norm(get(existing, "suburb"))
    c_phone, e_phone = _norm(get(candidate, "contact_number")), _norm(get(existing, "contact_number"))
    c_email, e_email = _norm(get(candidate, "email")), _norm(get(existing, "email"))
    c_price = get(candidate, "asking_price") or get(candidate, "monthly_rental")
    e_price = get(existing, "asking_price") or get(existing, "monthly_rental")
    c_type, e_type = _norm(get(candidate, "property_type")), _norm(get(existing, "property_type"))
    c_beds, e_beds = get(candidate, "bedrooms"), get(existing, "bedrooms")
    c_baths, e_baths = get(candidate, "bathrooms"), get(existing, "bathrooms")

    # --- Exact ---
    if c_url and e_url and c_url == e_url and c_source == e_source:
        return DuplicateClassification("exact", "Same source and listing URL")
    if c_ref and e_ref and c_ref == e_ref and c_source == e_source:
        return DuplicateClassification("exact", "Same source and listing reference")

    same_address = bool(c_addr) and bool(e_addr) and c_addr == e_addr and c_suburb == e_suburb
    same_contact = (bool(c_phone) and c_phone == e_phone) or (bool(c_email) and c_email == e_email)
    same_price = c_price is not None and e_price is not None and abs(float(c_price) - float(e_price)) < 0.01

    # --- Likely ---
    if same_address and (same_contact or same_price):
        reasons = ["same address+suburb"]
        if same_contact:
            reasons.append("same contact info")
        if same_price:
            reasons.append("same price")
        return DuplicateClassification("likely", " and ".join(reasons))

    # --- Possible ---
    if same_address:
        return DuplicateClassification("possible", "Same address+suburb, other fields differ")

    same_characteristics = (
        bool(c_type) and c_type == e_type and c_beds == e_beds and c_baths == e_baths
        and c_beds is not None
    )
    if same_contact and same_characteristics:
        return DuplicateClassification(
            "possible",
            "Same contact info and matching property characteristics, different address",
        )

    return DuplicateClassification("unique", "No matching signals found")


def find_duplicates(candidate, existing_pool: list) -> list[tuple]:
    """Returns [(existing_obj, DuplicateClassification), ...] for every
    existing record that isn't classified as 'unique'."""
    results = []
    for existing in existing_pool:
        classification = classify_duplicate(candidate, existing)
        if classification.match_type != "unique":
            results.append((existing, classification))
    return results

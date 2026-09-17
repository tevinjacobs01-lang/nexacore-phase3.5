"""Deterministic matching of normalized listings against saved searches."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchMatchResult:
    matched: bool
    reasons: tuple[str, ...]
    failed_criteria: tuple[str, ...]
    match_score: int


def _text(value) -> str:
    return str(value or "").strip().lower()


def _price(property) -> float | None:
    value = property.monthly_rental if property.listing_type == "rent" else property.asking_price
    return float(value) if value is not None else None


def _suburbs(search) -> set[str]:
    return {_text(value) for value in (search.suburbs or "").split(",") if _text(value)}


def match_saved_search(search, property, observation=None) -> SearchMatchResult:
    """Evaluate supported criteria without mutating the search or listing."""
    reasons: list[str] = []
    failed: list[str] = []

    expected_listing_type = "sale" if search.lead_type == "seller" else "rent"
    if _text(property.listing_type) != expected_listing_type:
        failed.append("listing type")
    else:
        reasons.append("listing type matched")

    if search.listing_type and _text(property.listing_type) != _text(search.listing_type):
        failed.append("listing type")
    elif search.listing_type:
        reasons.append("sale/rental criterion matched")

    if search.property_type and _text(property.property_type) != _text(search.property_type):
        failed.append("property type")
    elif search.property_type:
        reasons.append("property type matched")

    if search.bedrooms is not None and (property.bedrooms is None or property.bedrooms < search.bedrooms):
        failed.append("bedrooms")
    elif search.bedrooms is not None:
        reasons.append("bedrooms matched")

    if search.bathrooms is not None and (property.bathrooms is None or property.bathrooms < search.bathrooms):
        failed.append("bathrooms")
    elif search.bathrooms is not None:
        reasons.append("bathrooms matched")

    price = _price(property)
    if search.min_price is not None and (price is None or price < float(search.min_price)):
        failed.append("minimum price")
    if search.max_price is not None and (price is None or price > float(search.max_price)):
        failed.append("maximum price")
    if search.min_price is not None or search.max_price is not None:
        if "minimum price" not in failed and "maximum price" not in failed:
            reasons.append("price matched")

    locations = {_text(property.city), _text(property.province), _text(property.suburb), _text(property.address)}
    requested_suburbs = _suburbs(search)
    if requested_suburbs and not any(value in locations for value in requested_suburbs):
        failed.append("suburb")
    elif requested_suburbs:
        reasons.append("suburb matched")
    if search.location and _text(search.location) not in locations:
        failed.append("location")
    elif search.location:
        reasons.append("location matched")

    if search.minimum_score is not None and property.lead_score < search.minimum_score:
        failed.append("minimum score")
    elif search.minimum_score is not None:
        reasons.append("minimum score matched")

    match_score = round(len(reasons) / max(len(reasons) + len(failed), 1) * 100)
    return SearchMatchResult(not failed, tuple(reasons), tuple(failed), match_score)
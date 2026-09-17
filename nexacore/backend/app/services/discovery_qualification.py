"""Small, explainable discovery classification and qualification rules."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualificationResult:
    classification: str
    status: str
    score: int
    reason: str


def classify_listing(property) -> str:
    if property.listing_type == "sale":
        return "seller"
    if property.listing_type == "rent":
        return "landlord"
    return "unknown"


def qualify_listing(property, observation=None) -> QualificationResult:
    classification = classify_listing(property)
    if classification == "unknown":
        return QualificationResult("unknown", "review_required", 0, "Listing type is not sufficient to classify this opportunity.")

    score = min(100, int(property.lead_score or 0))
    owner_signal = property.is_owner_listed is True or property.seller_type == "owner"
    if classification == "seller":
        reason = "Property is listed by the owner; seller intent requires review." if owner_signal else "Property is listed for sale; ownership and seller intent require review."
    else:
        reason = "Property is advertised for rent by the owner; landlord intent requires review." if owner_signal else "Property is advertised for rent; landlord identity and intent require review."
    return QualificationResult(classification, "review_required", score, reason)
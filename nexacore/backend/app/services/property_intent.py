"""Detect property intent from permitted source text without inventing facts."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PropertyIntent:
    is_property_intent: bool
    listing_type: str | None
    advertiser_type: str
    confidence: str
    evidence: list[str]


@dataclass(frozen=True)
class IntentScore:
    score: int
    reasons: list[str]
    missing_information: list[str]
    confidence: str


SALE_PATTERNS = (
    r"\b(?:house|home|property|apartment|flat|plot|land)\b.*\bfor sale\b",
    r"\bfor sale\b",
    r"\bsell(?:ing)?\s+(?:my|our|the)?\s*(?:house|home|property|place)\b",
    r"\bprivate sale\b",
    r"\bowner\s+selling\b",
)
RENT_PATTERNS = (
    r"\b(?:house|home|property|apartment|flat|room)\b.*\b(?:to rent|for rent|available for rent)\b",
    r"\b(?:to rent|for rent|available for rent)\b",
    r"\blooking for a tenant\b",
    r"\bowner\s+letting\b",
    r"\blandlord\b",
)
SECONDARY_PATTERNS = {
    "urgent": r"\burgent|urgently|motivated|quickly|immediately\b",
    "price_change": r"\bprice\s*(?:reduced|drop|changed)|reduced price\b",
    "relocation": r"\bmoving|relocating\b",
    "offers": r"\boffers?\b|negotiable",
    "vacancy": r"\bvacant|available again|reposted|relisted\b",
}


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def detect_property_intent(text: str | None, metadata: dict | None = None) -> PropertyIntent:
    content = (text or "").strip()
    metadata = metadata or {}
    listing_type = metadata.get("listing_type")
    evidence: list[str] = []
    if not listing_type and _matches(content, SALE_PATTERNS):
        listing_type = "sale"
        evidence.append("sale intent detected from permitted source text")
    elif not listing_type and _matches(content, RENT_PATTERNS):
        listing_type = "rent"
        evidence.append("rental intent detected from permitted source text")
    elif listing_type in {"sale", "rent"}:
        evidence.append(f"{listing_type} intent supplied by source metadata")

    advertiser_type = str(metadata.get("advertiser_type") or "unknown").lower()
    if advertiser_type not in {"owner", "landlord", "agent", "agency", "developer", "property_company"}:
        advertiser_type = "unknown"
    lowered = content.lower()
    if advertiser_type == "unknown":
        if listing_type and re.search(r"\b(owner selling|owner letting|private sale|no agents?|selling my|selling our|letting my)\b", lowered):
            advertiser_type = "owner" if listing_type == "sale" else "landlord"
            evidence.append("explicit owner/private advertiser wording")
        elif re.search(r"\b(estate agent|property agent|rental agent|property manager)\b", lowered):
            advertiser_type = "agent"
            evidence.append("explicit agent/property manager wording")
        elif metadata.get("agency") or metadata.get("company"):
            advertiser_type = "agency"
            evidence.append("agency/company supplied by source metadata")

    confidence = "high" if listing_type and advertiser_type != "unknown" and evidence else "medium" if listing_type else "low"
    return PropertyIntent(bool(listing_type), listing_type, advertiser_type, confidence, evidence)


def score_property_intent(
    text: str | None,
    metadata: dict | None = None,
    target_locations: list[str] | None = None,
) -> IntentScore:
    """Score useful property intent without making score a capture gate."""
    metadata = metadata or {}
    content = (text or "").strip()
    intent = detect_property_intent(content, metadata)
    score = 0
    reasons: list[str] = []
    missing: list[str] = []
    if intent.listing_type:
        score += 30
        reasons.append(f"explicit {intent.listing_type} intent +30")
    for key, pattern in SECONDARY_PATTERNS.items():
        if re.search(pattern, content, flags=re.IGNORECASE):
            score += 8
            reasons.append(f"{key.replace('_', ' ')} signal +8")
    if intent.advertiser_type != "unknown":
        score += 20
        reasons.append(f"{intent.advertiser_type} wording or metadata +20")
    if metadata.get("contact_number") or metadata.get("phone"):
        score += 15
        reasons.append("phone available +15")
    if metadata.get("email") or metadata.get("contact_email"):
        score += 15
        reasons.append("email available +15")
    if metadata.get("address") or metadata.get("suburb") or metadata.get("city"):
        score += 10
        reasons.append("location supplied +10")
    if metadata.get("property_type"):
        score += 7
        reasons.append("property type identified +7")
    if metadata.get("asking_price") or metadata.get("monthly_rental") or metadata.get("price"):
        score += 5
        reasons.append("price supplied +5")
    location_values = " ".join(str(metadata.get(field) or "") for field in ("address", "suburb", "city", "province"))
    targets = {value.strip().lower() for value in (target_locations or []) if value.strip()}
    if targets and any(target in location_values.lower() for target in targets):
        score += 10
        reasons.append("target location matched +10")

    for label, field in (("address", "address"), ("price", "asking_price"), ("property type", "property_type")):
        if not metadata.get(field):
            missing.append(label)
    if not metadata.get("contact_number") and not metadata.get("phone") and not metadata.get("email"):
        missing.append("contact")
    confidence = "high" if intent.is_property_intent and not missing else "medium" if intent.is_property_intent else "low"
    return IntentScore(min(100, score), reasons, missing, confidence)
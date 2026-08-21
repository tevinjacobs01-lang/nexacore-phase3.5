"""
Configurable lead scoring engine.

Each LeadScoreRule row has a rule_key that maps to an evaluator below, a
points value, an is_active flag, and an optional `config` string (simple
comma-separated values or a single number, kept deliberately plain-text so
non-technical admins editing via the settings page don't need to write JSON).

Default rules (matching the spec) are seeded on app startup — see
DEFAULT_RULES below and app/main.py's startup event.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, date

from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.lead_score import LeadScoreRule, PropertyScoreHistory

# (rule_key, name, points, config) — seeded once if the rules table is empty.
DEFAULT_RULES: list[tuple[str, str, int, str | None]] = [
    ("days_on_market_gt_30", "Days on Market > 30", 10, "30"),
    ("days_on_market_gt_60", "Days on Market > 60", 20, "60"),
    ("days_on_market_gt_90", "Days on Market > 90", 30, "90"),
    ("preferred_suburb", "Preferred Suburb", 20, ""),  # config: comma list of suburbs
    ("price_range_match", "Price Range Match", 15, "0,0"),  # config: "min,max"
    ("luxury_property", "Luxury Property", 10, "3000000"),  # config: price threshold
    ("rental_opportunity", "Rental Opportunity", 10, None),
    ("relisted_property", "Relisted Property", 20, None),
    ("recent_price_reduction", "Recent Price Reduction", 25, "30"),  # config: lookback days
]


def _parse_list(config: str | None) -> list[str]:
    if not config:
        return []
    return [v.strip().lower() for v in config.split(",") if v.strip()]


def _parse_range(config: str | None) -> tuple[float | None, float | None]:
    if not config:
        return None, None
    parts = [p.strip() for p in config.split(",")]
    try:
        lo = float(parts[0]) if parts[0] else None
        hi = float(parts[1]) if len(parts) > 1 and parts[1] else None
        return lo, hi
    except (ValueError, IndexError):
        return None, None


def _evaluate_rule(rule: LeadScoreRule, prop: Property) -> bool:
    key = rule.rule_key

    if key == "days_on_market_gt_30":
        threshold = float(rule.config or 30)
        return (prop.days_on_market or 0) > threshold

    if key == "days_on_market_gt_60":
        threshold = float(rule.config or 60)
        return (prop.days_on_market or 0) > threshold

    if key == "days_on_market_gt_90":
        threshold = float(rule.config or 90)
        return (prop.days_on_market or 0) > threshold

    if key == "preferred_suburb":
        suburbs = _parse_list(rule.config)
        return bool(prop.suburb) and prop.suburb.strip().lower() in suburbs

    if key == "price_range_match":
        lo, hi = _parse_range(rule.config)
        price = prop.asking_price or prop.monthly_rental
        if price is None or (lo is None and hi is None):
            return False
        if lo is not None and price < lo:
            return False
        if hi is not None and price > hi:
            return False
        return True

    if key == "luxury_property":
        threshold = float(rule.config) if rule.config else None
        return threshold is not None and (prop.asking_price or 0) >= threshold

    if key == "rental_opportunity":
        return prop.listing_type == "rent"

    if key == "relisted_property":
        return bool(prop.is_relisted)

    if key == "recent_price_reduction":
        if not prop.price_reduced_at:
            return False
        lookback_days = int(rule.config) if rule.config else 30
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        reduced_at = prop.price_reduced_at
        if isinstance(reduced_at, date) and not isinstance(reduced_at, datetime):
            reduced_at = datetime.combine(reduced_at, datetime.min.time())
        return reduced_at >= cutoff

    # Unknown rule_key — ignore rather than error, so a bad admin edit
    # doesn't take down scoring for every property.
    return False


def score_property(prop: Property, rules: list[LeadScoreRule]) -> tuple[int, dict[str, int]]:
    total = 0
    breakdown: dict[str, int] = {}
    for rule in rules:
        if not rule.is_active:
            continue
        if _evaluate_rule(rule, prop):
            total += rule.points
            breakdown[rule.rule_key] = rule.points
    return total, breakdown


def recompute_score(db: Session, prop: Property) -> Property:
    rules = db.query(LeadScoreRule).filter(LeadScoreRule.is_active.is_(True)).all()
    total, breakdown = score_property(prop, rules)

    prop.lead_score = total
    db.add(
        PropertyScoreHistory(
            property_id=prop.id,
            score=total,
            breakdown=json.dumps(breakdown),
        )
    )
    return prop


def recompute_all_scores(db: Session) -> int:
    properties = db.query(Property).all()
    for prop in properties:
        recompute_score(db, prop)
    db.commit()
    return len(properties)


def seed_default_rules(db: Session) -> None:
    """Insert default rules if the table is empty. Safe to call on every startup."""
    if db.query(LeadScoreRule).count() > 0:
        return
    for rule_key, name, points, config in DEFAULT_RULES:
        db.add(LeadScoreRule(rule_key=rule_key, name=name, points=points, config=config))
    db.commit()

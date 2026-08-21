"""
Listing history tracking (Sprint 14).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.listing_history import ListingHistory


def record_change(
    db: Session,
    prop: Property,
    *,
    new_price: float | None = None,
    new_description: str | None = None,
    new_status: str | None = None,
) -> ListingHistory | None:
    """Compares the given new_* values against the property's current state
    and, if anything actually changed, writes one ListingHistory row and
    applies the update to the property. Returns None if nothing changed."""
    changed = False
    entry = ListingHistory(property_id=prop.id)

    if new_price is not None and prop.asking_price != new_price:
        entry.previous_price = prop.asking_price
        entry.new_price = new_price
        prop.asking_price = new_price
        changed = True

    if new_description is not None and prop.notes != new_description:
        entry.previous_description = prop.notes
        entry.new_description = new_description
        prop.notes = new_description
        changed = True

    if new_status is not None and prop.listing_status != new_status:
        entry.previous_status = prop.listing_status
        entry.new_status = new_status
        prop.listing_status = new_status
        changed = True

    if not changed:
        return None

    db.add(entry)
    return entry

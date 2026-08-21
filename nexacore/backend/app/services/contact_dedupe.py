"""
Duplicate-contact prevention (Sprint 21). Simpler than the listing dedupe
engine (Sprint 13) since contacts only need phone/email/name matching —
but reuses the same normalization functions so "082 123 4567" and
"+27821234567" are recognized as the same person.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.services.normalization import normalize_phone, normalize_email


def find_existing_contact(db: Session, *, name: str | None, phone: str | None, email: str | None) -> Contact | None:
    """Returns an existing Contact if phone or email normalizes to a match.
    Falls back to exact case-insensitive name match only if neither phone
    nor email is provided (weak signal, used as a last resort)."""
    norm_phone = normalize_phone(phone)
    norm_email = normalize_email(email)

    if norm_phone:
        match = db.query(Contact).filter(Contact.phone == norm_phone).first()
        if match:
            return match

    if norm_email:
        match = db.query(Contact).filter(Contact.email == norm_email).first()
        if match:
            return match

    if not norm_phone and not norm_email and name:
        match = db.query(Contact).filter(Contact.name.ilike(name.strip())).first()
        if match:
            return match

    return None

"""
Contact management endpoints (Sprint 21). Extends the minimal Contacts
endpoint added during Phase 2 verification with the full field set and
duplicate-prevention flow.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.contact import Contact, CONTACT_TYPES, PREFERRED_CONTACT_METHODS
from app.models.property import Property
from app.models.contact_property import ContactProperty
from app.schemas.contact import ContactCreate, ContactUpdate, ContactOut
from app.services.contact_dedupe import find_existing_contact

router = APIRouter()


@router.get("/", response_model=list[ContactOut])
def list_contacts(
    contact_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Contact)
    if contact_type:
        query = query.filter(Contact.contact_type == contact_type)
    return query.order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=ContactOut, status_code=201)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if payload.contact_type and payload.contact_type not in CONTACT_TYPES:
        raise HTTPException(status_code=400, detail=f"contact_type must be one of {sorted(CONTACT_TYPES)}")
    if payload.preferred_contact_method and payload.preferred_contact_method not in PREFERRED_CONTACT_METHODS:
        raise HTTPException(
            status_code=400,
            detail=f"preferred_contact_method must be one of {sorted(PREFERRED_CONTACT_METHODS)}",
        )

    if not payload.force_create:
        existing = find_existing_contact(db, name=payload.name, phone=payload.phone, email=payload.email)
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "A matching contact already exists.",
                    "existing_contact_id": str(existing.id),
                    "hint": "Resubmit with force_create=true to create a separate contact anyway.",
                },
            )

    from app.services.normalization import normalize_phone, normalize_email
    data = payload.model_dump(exclude={"force_create"})
    data["phone"] = normalize_phone(data["phone"])
    data["email"] = normalize_email(data["email"])

    contact = Contact(**data)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.post("/{contact_id}/listings/{property_id}", status_code=201)
def link_contact_to_listing(
    contact_id: uuid.UUID,
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    if not db.query(Contact).filter(Contact.id == contact_id).first():
        raise HTTPException(status_code=404, detail="Contact not found")
    if not db.query(Property).filter(Property.id == property_id).first():
        raise HTTPException(status_code=404, detail="Property not found")

    existing_link = (
        db.query(ContactProperty)
        .filter(ContactProperty.contact_id == contact_id, ContactProperty.property_id == property_id)
        .first()
    )
    if existing_link:
        return {"detail": "Already linked"}

    db.add(ContactProperty(contact_id=contact_id, property_id=property_id))
    db.commit()
    return {"detail": "Linked"}


@router.get("/{contact_id}/listings")
def list_contact_listings(contact_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    links = db.query(ContactProperty).filter(ContactProperty.contact_id == contact_id).all()
    property_ids = [link.property_id for link in links]
    return db.query(Property).filter(Property.id.in_(property_ids)).all()

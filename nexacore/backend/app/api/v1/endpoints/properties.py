"""
Property CRUD + filtering + search.

Filters supported (all optional, combinable): province, city, suburb,
min/max asking price, min/max monthly rental, bedrooms, bathrooms, property_type,
listing_type (sale/rent), min/max days on market, min/max lead score,
contact_status, listing_source.

Search (`q`) matches address, suburb, listing_reference, agent_name, contact_number.
Sorting via `sort_by` + `sort_dir`.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, asc, desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyOut

router = APIRouter()

SORTABLE_FIELDS = {
    "created_at": Property.created_at,
    "asking_price": Property.asking_price,
    "days_on_market": Property.days_on_market,
    "lead_score": Property.lead_score,
    "listing_date": Property.listing_date,
}


@router.get("/", response_model=list[PropertyOut])
def list_properties(
    skip: int = 0,
    limit: int = 50,
    q: str | None = Query(None, description="Free-text search"),
    province: str | None = None,
    city: str | None = None,
    suburb: str | None = None,
    property_type: str | None = None,
    listing_type: str | None = Query(None, pattern="^(sale|rent)$"),
    contact_status: str | None = None,
    listing_source: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_rental: float | None = None,
    max_rental: float | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    min_days_on_market: int | None = None,
    max_days_on_market: int | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    sort_by: str = Query("created_at", description="One of: " + ", ".join(SORTABLE_FIELDS)),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Property)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Property.address.ilike(like),
                Property.suburb.ilike(like),
                Property.listing_reference.ilike(like),
                Property.agent_name.ilike(like),
                Property.contact_number.ilike(like),
            )
        )

    if province:
        query = query.filter(Property.province.ilike(province))
    if city:
        query = query.filter(Property.city.ilike(city))
    if suburb:
        query = query.filter(Property.suburb.ilike(suburb))
    if property_type:
        query = query.filter(Property.property_type.ilike(property_type))
    if listing_type:
        query = query.filter(Property.listing_type == listing_type)
    if contact_status:
        query = query.filter(Property.contact_status == contact_status)
    if listing_source:
        query = query.filter(Property.listing_source.ilike(listing_source))

    if min_price is not None:
        query = query.filter(Property.asking_price >= min_price)
    if max_price is not None:
        query = query.filter(Property.asking_price <= max_price)
    if min_rental is not None:
        query = query.filter(Property.monthly_rental >= min_rental)
    if max_rental is not None:
        query = query.filter(Property.monthly_rental <= max_rental)

    if bedrooms is not None:
        query = query.filter(Property.bedrooms == bedrooms)
    if bathrooms is not None:
        query = query.filter(Property.bathrooms == bathrooms)

    if min_days_on_market is not None:
        query = query.filter(Property.days_on_market >= min_days_on_market)
    if max_days_on_market is not None:
        query = query.filter(Property.days_on_market <= max_days_on_market)

    if min_score is not None:
        query = query.filter(Property.lead_score >= min_score)
    if max_score is not None:
        query = query.filter(Property.lead_score <= max_score)

    sort_col = SORTABLE_FIELDS.get(sort_by, Property.created_at)
    query = query.order_by(asc(sort_col) if sort_dir == "asc" else desc(sort_col))

    return query.offset(skip).limit(limit).all()


@router.get("/count")
def count_properties(
    q: str | None = None,
    contact_status: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Property)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Property.address.ilike(like), Property.suburb.ilike(like))
        )
    if contact_status:
        query = query.filter(Property.contact_status == contact_status)
    return {"count": query.count()}


@router.post("/", response_model=PropertyOut, status_code=201)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    prop = Property(**payload.model_dump())
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(property_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@router.patch("/{property_id}", response_model=PropertyOut)
def update_property(
    property_id: uuid.UUID,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)

    db.commit()
    db.refresh(prop)
    return prop


@router.delete("/{property_id}", status_code=204)
def delete_property(property_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    db.delete(prop)
    db.commit()

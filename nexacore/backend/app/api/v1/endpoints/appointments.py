"""
Appointment management endpoints (Sprint 26).
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment, APPOINTMENT_STATUSES, APPOINTMENT_TYPES
from app.models.lead import Lead
from app.models.contact import Contact
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentOut

router = APIRouter()


@router.get("/", response_model=list[AppointmentOut])
def list_appointments(
    status: str | None = None,
    lead_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Appointment)
    if status:
        query = query.filter(Appointment.status == status)
    if lead_id:
        query = query.filter(Appointment.lead_id == lead_id)
    return query.order_by(Appointment.starts_at.asc()).offset(skip).limit(limit).all()


@router.post("/", response_model=AppointmentOut, status_code=201)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if payload.appointment_type not in APPOINTMENT_TYPES:
        raise HTTPException(status_code=400, detail=f"appointment_type must be one of {sorted(APPOINTMENT_TYPES)}")
    if not payload.lead_id and not payload.contact_id:
        raise HTTPException(status_code=400, detail="Provide at least one of lead_id or contact_id")
    if payload.lead_id and not db.query(Lead).filter(Lead.id == payload.lead_id).first():
        raise HTTPException(status_code=404, detail="Lead not found")
    if payload.contact_id and not db.query(Contact).filter(Contact.id == payload.contact_id).first():
        raise HTTPException(status_code=404, detail="Contact not found")

    appointment = Appointment(**payload.model_dump())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.patch("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in APPOINTMENT_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(APPOINTMENT_STATUSES)}")

    for field, value in updates.items():
        setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)
    return appointment

"""
Communication template endpoints (Sprint 29). Rendering only ever produces
text for the agent to copy/review — nothing here sends anything.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.communication_template import CommunicationTemplate, TEMPLATE_TYPES
from app.models.lead import Lead
from app.models.property import Property
from app.models.contact import Contact
from app.schemas.communication_template import (
    TemplateCreate, TemplateUpdate, TemplateOut, RenderTemplateRequest,
)
from app.services.templates import render_template, build_lead_variables

router = APIRouter()


@router.get("/", response_model=list[TemplateOut])
def list_templates(
    template_type: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(CommunicationTemplate)
    if template_type:
        query = query.filter(CommunicationTemplate.template_type == template_type)
    return query.order_by(CommunicationTemplate.name).all()


@router.post("/", response_model=TemplateOut, status_code=201)
def create_template(payload: TemplateCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if payload.template_type not in TEMPLATE_TYPES:
        raise HTTPException(status_code=400, detail=f"template_type must be one of {sorted(TEMPLATE_TYPES)}")
    template = CommunicationTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.patch("/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: uuid.UUID,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    template = db.query(CommunicationTemplate).filter(CommunicationTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.post("/{template_id}/render")
def render(
    template_id: uuid.UUID,
    payload: RenderTemplateRequest,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    template = db.query(CommunicationTemplate).filter(CommunicationTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    variables: dict[str, str | None] = {}
    if payload.lead_id:
        lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        prop = db.query(Property).filter(Property.id == lead.property_id).first()
        contact = db.query(Contact).filter(Contact.id == lead.contact_id).first() if lead.contact_id else None
        variables = build_lead_variables(
            contact_name=contact.name if contact else None,
            property_address=prop.address if prop else None,
            property_price=float(prop.asking_price) if prop and prop.asking_price else None,
            suburb=prop.suburb if prop else None,
            listing_url=prop.listing_url if prop else None,
        )

    variables.update(payload.extra_variables)

    return {
        "subject": render_template(template.subject, variables) if template.subject else None,
        "body": render_template(template.body, variables),
    }

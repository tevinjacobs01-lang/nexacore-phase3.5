"""Centralized record access checks for the single-workspace data model."""
from __future__ import annotations

import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.capture import Capture
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.property import Property
from app.models.user import User
from app.models.task import Task
from app.models.follow_up import FollowUp
from app.models.appointment import Appointment
from sqlalchemy import or_


def is_admin(user: User) -> bool:
    """Return whether a user has workspace-wide administrative access.

    ``owner`` is already treated as an administrator by ``require_admin``;
    keeping that rule here prevents ownership checks from accidentally
    excluding the workspace owner.
    """
    return user.role in {"owner", "admin"}


def leads_visible_to_user(query, user: User):
    """Scope a Lead query to records visible to ``user``.

    Ordinary agents never receive unassigned leads: the equality predicate
    deliberately excludes NULL ``assigned_agent_id`` values.
    """
    if is_admin(user):
        return query
    return query.filter(Lead.assigned_agent_id == user.id)


def properties_visible_to_user(db: Session, query, user: User):
    if is_admin(user):
        return query
    return query.filter(
        or_(
            Property.created_by == user.id,
            Property.id.in_(db.query(Lead.property_id).filter(Lead.assigned_agent_id == user.id)),
        )
    )


def contacts_visible_to_user(db: Session, query, user: User):
    if is_admin(user):
        return query
    return query.filter(
        or_(
            Contact.created_by == user.id,
            Contact.id.in_(db.query(Lead.contact_id).filter(Lead.assigned_agent_id == user.id)),
        )
    )




def require_lead_access(lead: Lead | None, user: User) -> Lead:
    """Return an accessible lead, hiding inaccessible records as not found."""
    if lead is None or not can_access_lead(None, lead, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


def can_access_lead(db: Session, lead: Lead, user: User) -> bool:
    return is_admin(user) or lead.assigned_agent_id == user.id


def can_access_property(db: Session, property_id: uuid.UUID, user: User) -> bool:
    if is_admin(user):
        return True
    return db.query(Property).filter(
        Property.id == property_id,
        Property.created_by == user.id,
    ).first() is not None or db.query(Lead).filter(
        Lead.property_id == property_id,
        Lead.assigned_agent_id == user.id,
    ).first() is not None


def can_access_contact(db: Session, contact_id: uuid.UUID, user: User) -> bool:
    if is_admin(user):
        return True
    return db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.created_by == user.id,
    ).first() is not None or db.query(Lead).filter(
        Lead.contact_id == contact_id,
        Lead.assigned_agent_id == user.id,
    ).first() is not None


def can_access_entity(db: Session, entity_type: str, entity_id: uuid.UUID, user: User) -> bool:
    if entity_type == "lead":
        lead = db.query(Lead).filter(Lead.id == entity_id).first()
        return lead is not None and can_access_lead(db, lead, user)
    if entity_type == "listing":
        return can_access_property(db, entity_id, user)
    if entity_type == "contact":
        return can_access_contact(db, entity_id, user)
    if entity_type == "capture":
        return is_admin(user) or db.query(Capture).filter(
            Capture.id == entity_id, Capture.user_id == user.id
        ).first() is not None
    return False


def can_access_task(db: Session, task: Task, user: User) -> bool:
    return is_admin(user) or task.assigned_user_id == user.id or task.created_by == user.id or (
        task.lead_id is not None and db.query(Lead).filter(
            Lead.id == task.lead_id, Lead.assigned_agent_id == user.id
        ).first() is not None
    )


def can_access_follow_up(db: Session, follow_up: FollowUp, user: User) -> bool:
    return is_admin(user) or follow_up.created_by == user.id or (
        follow_up.lead_id is not None and db.query(Lead).filter(
            Lead.id == follow_up.lead_id, Lead.assigned_agent_id == user.id
        ).first() is not None
    )


def can_access_appointment(db: Session, appointment: Appointment, user: User) -> bool:
    return is_admin(user) or appointment.created_by == user.id or (
        appointment.lead_id is not None and db.query(Lead).filter(
            Lead.id == appointment.lead_id, Lead.assigned_agent_id == user.id
        ).first() is not None
    )

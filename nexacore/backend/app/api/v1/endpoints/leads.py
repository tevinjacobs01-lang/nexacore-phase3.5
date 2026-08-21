"""
Lead pipeline endpoints. Sprint 27 expands the pipeline to the full 11-stage
sales pipeline and records every transition to LeadStageHistory. Sprint 28
adds assignment with a full audit trail via the Assignment table.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.lead import Lead, LEAD_PIPELINE_STAGES, resolve_stage
from app.models.lead_stage_history import LeadStageHistory
from app.models.assignment import Assignment
from app.models.property import Property
from app.models.contact import Contact
from app.models.user import User
from app.schemas.lead import (
    LeadCreate, LeadUpdate, LeadOut, LEAD_STATUSES, LEAD_PRIORITIES, AssignLeadRequest,
)

router = APIRouter()


@router.get("/", response_model=list[LeadOut])
def list_leads(
    status: str | None = None,
    priority: str | None = None,
    assigned_agent_id: uuid.UUID | None = None,
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.status == status)
    if priority:
        query = query.filter(Lead.priority == priority)
    if assigned_agent_id:
        query = query.filter(Lead.assigned_agent_id == assigned_agent_id)
    if unassigned_only:
        query = query.filter(Lead.assigned_agent_id.is_(None))
    return query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/pipeline")
def pipeline_view(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Leads grouped by pipeline stage, for a kanban-style board. Any lead
    still holding a legacy Phase-2 status is bucketed under its Sprint-27
    equivalent via resolve_stage() rather than falling through the cracks."""
    result = {stage: [] for stage in LEAD_PIPELINE_STAGES}
    for lead in db.query(Lead).order_by(Lead.created_at.desc()).all():
        stage = resolve_stage(lead.status)
        result.setdefault(stage, []).append(LeadOut.model_validate(lead))
    return result


@router.get("/{lead_id}/detail")
def lead_detail(lead_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Sprint 30 — the complete lead profile: property, contact, status,
    stage, priority, notes, activity timeline, tasks, follow-ups,
    appointments, assignment. Answers: who / what property / what happened /
    what next / when."""
    from app.models.interaction import Interaction
    from app.models.task import Task
    from app.models.follow_up import FollowUp
    from app.models.appointment import Appointment

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    prop = db.query(Property).filter(Property.id == lead.property_id).first()
    contact = db.query(Contact).filter(Contact.id == lead.contact_id).first() if lead.contact_id else None

    timeline = (
        db.query(Interaction)
        .filter((Interaction.lead_id == lead_id) | (Interaction.contact_id == lead.contact_id))
        .order_by(Interaction.occurred_at.desc())
        .limit(50)
        .all()
    )
    tasks = db.query(Task).filter(Task.lead_id == lead_id).order_by(Task.due_date.asc().nullslast()).all()
    follow_ups = (
        db.query(FollowUp)
        .filter(FollowUp.lead_id == lead_id)
        .order_by(FollowUp.due_at.asc())
        .all()
    )
    appointments = (
        db.query(Appointment)
        .filter(Appointment.lead_id == lead_id)
        .order_by(Appointment.starts_at.asc())
        .all()
    )
    stage_history = (
        db.query(LeadStageHistory)
        .filter(LeadStageHistory.lead_id == lead_id)
        .order_by(LeadStageHistory.changed_at.asc())
        .all()
    )

    return {
        "lead": LeadOut.model_validate(lead),
        "property": prop,
        "contact": contact,
        "activity_timeline": timeline,
        "tasks": tasks,
        "follow_ups": follow_ups,
        "appointments": appointments,
        "stage_history": [
            {"from_stage": h.from_stage, "to_stage": h.to_stage, "changed_at": h.changed_at}
            for h in stage_history
        ],
    }


@router.post("/", response_model=LeadOut, status_code=201)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if payload.priority not in LEAD_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"priority must be one of {sorted(LEAD_PRIORITIES)}")

    prop = db.query(Property).filter(Property.id == payload.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    if payload.contact_id:
        contact = db.query(Contact).filter(Contact.id == payload.contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.flush()
    db.add(LeadStageHistory(lead_id=lead.id, from_stage=None, to_stage=lead.status))
    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in LEAD_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(LEAD_STATUSES)}")
    if "priority" in updates and updates["priority"] not in LEAD_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"priority must be one of {sorted(LEAD_PRIORITIES)}")

    if updates.get("status") == "contacted":
        lead.last_contacted_at = datetime.utcnow()

    if "status" in updates and updates["status"] != lead.status:
        db.add(LeadStageHistory(lead_id=lead.id, from_stage=lead.status, to_stage=updates["status"], changed_by=user.id))

    for field, value in updates.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}/stage-history")
def get_stage_history(lead_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return (
        db.query(LeadStageHistory)
        .filter(LeadStageHistory.lead_id == lead_id)
        .order_by(LeadStageHistory.changed_at.asc())
        .all()
    )


@router.get("/conversion-rates")
def conversion_rates(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Sprint 27 — conversion rate between each consecutive pair of pipeline
    stages, based on how many leads that ever reached stage N also reached
    stage N+1 at some point (per LeadStageHistory)."""
    all_history = db.query(LeadStageHistory).all()
    reached: dict[str, set] = {stage: set() for stage in LEAD_PIPELINE_STAGES}
    for h in all_history:
        if h.to_stage in reached:
            reached[h.to_stage].add(h.lead_id)

    rates = []
    for i in range(len(LEAD_PIPELINE_STAGES) - 1):
        current_stage, next_stage = LEAD_PIPELINE_STAGES[i], LEAD_PIPELINE_STAGES[i + 1]
        current_count = len(reached[current_stage])
        next_count = len(reached[next_stage])
        rate = (next_count / current_count * 100) if current_count > 0 else None
        rates.append({
            "from_stage": current_stage, "to_stage": next_stage,
            "reached_from": current_count, "reached_to": next_count,
            "conversion_rate_pct": round(rate, 1) if rate is not None else None,
        })
    return rates


# ---- Sprint 28: Lead Assignment ----

@router.post("/{lead_id}/assign", response_model=LeadOut)
def assign_lead(
    lead_id: uuid.UUID,
    payload: AssignLeadRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Assign or reassign a lead. Marks any prior assignment as no longer
    current and appends a new Assignment row — full history preserved."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    agent = db.query(User).filter(User.id == payload.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent (user) not found")

    db.query(Assignment).filter(Assignment.lead_id == lead_id, Assignment.is_current.is_(True)).update(
        {"is_current": False}
    )
    db.add(Assignment(lead_id=lead_id, agent_id=payload.agent_id, assigned_by=user.id, is_current=True))
    lead.assigned_agent_id = payload.agent_id

    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}/assignment-history")
def assignment_history(lead_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return (
        db.query(Assignment)
        .filter(Assignment.lead_id == lead_id)
        .order_by(Assignment.assigned_at.asc())
        .all()
    )


@router.get("/unassigned", response_model=list[LeadOut])
def unassigned_leads(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return (
        db.query(Lead)
        .filter(Lead.assigned_agent_id.is_(None))
        .order_by(Lead.created_at.desc())
        .all()
    )

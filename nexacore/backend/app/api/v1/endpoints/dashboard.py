"""
Dashboard summary stats and chart data.
"""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.property import Property
from app.models.scan_job import ScanJob
from app.models.source import Source
from app.models.lead import Lead

router = APIRouter()


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    today_start = datetime.combine(date.today(), datetime.min.time())

    total = db.query(func.count(Property.id)).scalar()
    new_today = db.query(func.count(Property.id)).filter(Property.created_at >= today_start).scalar()
    hot = db.query(func.count(Property.id)).filter(Property.lead_score >= 70).scalar()
    warm = db.query(func.count(Property.id)).filter(
        Property.lead_score >= 40, Property.lead_score < 70
    ).scalar()
    follow_ups_due_today = db.query(func.count(Property.id)).filter(
        Property.follow_up_date == date.today()
    ).scalar()
    recently_contacted = db.query(func.count(Property.id)).filter(
        Property.last_contacted_at >= datetime.utcnow() - timedelta(days=7)
    ).scalar()
    week_start = datetime.combine(date.today() - timedelta(days=date.today().weekday()), datetime.min.time())
    new_this_week = db.query(func.count(Property.id)).filter(Property.created_at >= week_start).scalar()
    active_leads = db.query(func.count(Lead.id)).filter(
        Lead.status.notin_(["converted", "not_interested", "closed"])
    ).scalar()
    appointments = db.query(func.count(Lead.id)).filter(Lead.status == "appointment").scalar()
    converted_leads = db.query(func.count(Lead.id)).filter(Lead.status == "converted").scalar()

    return {
        "total_listings": total,
        "new_listings_today": new_today,
        "new_listings_this_week": new_this_week,
        "hot_leads": hot,
        "warm_leads": warm,
        "follow_ups_due_today": follow_ups_due_today,
        "recently_contacted": recently_contacted,
        "active_leads": active_leads,
        "appointments": appointments,
        "converted_leads": converted_leads,
    }


@router.get("/charts/by-suburb")
def listings_by_suburb(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    rows = (
        db.query(Property.suburb, func.count(Property.id))
        .filter(Property.suburb.isnot(None))
        .group_by(Property.suburb)
        .order_by(func.count(Property.id).desc())
        .limit(15)
        .all()
    )
    return [{"suburb": suburb, "count": count} for suburb, count in rows]


@router.get("/charts/by-property-type")
def listings_by_property_type(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    rows = (
        db.query(Property.property_type, func.count(Property.id))
        .filter(Property.property_type.isnot(None))
        .group_by(Property.property_type)
        .order_by(func.count(Property.id).desc())
        .all()
    )
    return [{"property_type": ptype, "count": count} for ptype, count in rows]


@router.get("/charts/by-price-range")
def listings_by_price_range(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    # Fixed buckets — tune to local market as needed.
    buckets = [
        (0, 500_000, "< 500k"),
        (500_000, 1_000_000, "500k–1M"),
        (1_000_000, 2_000_000, "1M–2M"),
        (2_000_000, 5_000_000, "2M–5M"),
        (5_000_000, None, "5M+"),
    ]
    results = []
    for lo, hi, label in buckets:
        q = db.query(func.count(Property.id)).filter(Property.asking_price >= lo)
        if hi is not None:
            q = q.filter(Property.asking_price < hi)
        results.append({"range": label, "count": q.scalar()})
    return results


@router.get("/charts/score-distribution")
def score_distribution(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    buckets = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]
    results = []
    for lo, hi in buckets:
        count = (
            db.query(func.count(Property.id))
            .filter(Property.lead_score >= lo, Property.lead_score < hi)
            .scalar()
        )
        results.append({"range": f"{lo}-{hi - 1}", "count": count})
    return results


@router.get("/collection")
def collection_overview(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Sprint 20 — Collection section: active sources, recent scans, errors."""
    sources = db.query(Source).order_by(Source.name).all()
    recent_scans = db.query(ScanJob).order_by(ScanJob.created_at.desc()).limit(10).all()
    total_errors_last_10 = sum(s.error_count for s in recent_scans)

    return {
        "active_sources": sum(1 for s in sources if s.is_enabled),
        "total_sources": len(sources),
        "sources": [
            {
                "id": s.id, "name": s.name, "is_enabled": s.is_enabled,
                "last_successful_scan_at": s.last_successful_scan_at,
                "last_error": s.last_error,
                "listings_collected_count": s.listings_collected_count,
            }
            for s in sources
        ],
        "recent_scans": [
            {
                "id": sc.id, "source_id": sc.source_id, "status": sc.status,
                "started_at": sc.started_at, "finished_at": sc.finished_at,
                "listings_discovered": sc.listings_discovered,
                "new_listings": sc.new_listings, "error_count": sc.error_count,
            }
            for sc in recent_scans
        ],
        "errors_last_10_scans": total_errors_last_10,
    }


@router.get("/leads")
def leads_overview(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Sprint 20 — Leads section: highest priority, new, follow-ups due,
    recently contacted, converted."""
    highest_priority = (
        db.query(Lead)
        .filter(Lead.priority == "high", Lead.status.notin_(["converted", "closed", "not_interested"]))
        .order_by(Lead.created_at.desc())
        .limit(10)
        .all()
    )
    new_leads = db.query(Lead).filter(Lead.status == "new").order_by(Lead.created_at.desc()).limit(10).all()
    follow_ups = (
        db.query(Lead)
        .filter(Lead.next_follow_up <= date.today(), Lead.status.notin_(["converted", "closed"]))
        .order_by(Lead.next_follow_up.asc())
        .all()
    )
    recently_contacted = (
        db.query(Lead)
        .filter(Lead.last_contacted_at >= datetime.utcnow() - timedelta(days=7))
        .order_by(Lead.last_contacted_at.desc())
        .limit(10)
        .all()
    )
    converted = db.query(Lead).filter(Lead.status == "converted").order_by(Lead.created_at.desc()).limit(10).all()

    def brief(lead):
        return {
            "id": lead.id, "property_id": lead.property_id, "status": lead.status,
            "priority": lead.priority, "next_follow_up": lead.next_follow_up,
        }

    return {
        "highest_priority": [brief(l) for l in highest_priority],
        "new_leads": [brief(l) for l in new_leads],
        "follow_ups_due": [brief(l) for l in follow_ups],
        "recently_contacted": [brief(l) for l in recently_contacted],
        "converted": [brief(l) for l in converted],
    }


@router.get("/crm")
def crm_dashboard(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Sprint 30 — CRM dashboard: lead metrics, follow-up metrics,
    conversion metrics, and agent metrics (architecture prepared for
    multi-agent; works today with however many users exist)."""
    from app.models.lead import LEAD_PIPELINE_STAGES, resolve_stage
    from app.models.lead_stage_history import LeadStageHistory
    from app.models.follow_up import FollowUp
    from app.models.appointment import Appointment
    from app.models.interaction import Interaction
    from app.models.user import User

    # --- Lead metrics ---
    all_leads = db.query(Lead).all()
    stage_counts = {stage: 0 for stage in LEAD_PIPELINE_STAGES}
    for lead in all_leads:
        stage_counts[resolve_stage(lead.status)] = stage_counts.get(resolve_stage(lead.status), 0) + 1

    lead_metrics = {
        "total_leads": len(all_leads),
        "new": stage_counts.get("new", 0),
        "contacted": stage_counts.get("contacted", 0),
        "responded": stage_counts.get("responded", 0),
        "qualified": stage_counts.get("qualified", 0),
        "appointment": stage_counts.get("appointment", 0),
        "won": stage_counts.get("won", 0),
        "lost": stage_counts.get("lost", 0),
    }

    # --- Follow-up metrics ---
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), datetime.min.time())
    today_end = datetime.combine(now.date(), datetime.max.time())
    follow_up_metrics = {
        "due_today": db.query(func.count(FollowUp.id)).filter(
            FollowUp.status == "pending", FollowUp.due_at >= today_start, FollowUp.due_at <= today_end
        ).scalar(),
        "overdue": db.query(func.count(FollowUp.id)).filter(
            FollowUp.status == "pending", FollowUp.due_at < today_start
        ).scalar(),
        "upcoming": db.query(func.count(FollowUp.id)).filter(
            FollowUp.status == "pending", FollowUp.due_at > today_end
        ).scalar(),
    }

    # --- Conversion metrics (contact->response->qualified->appointment->won) ---
    history = db.query(LeadStageHistory).all()
    reached: dict[str, set] = {}
    for h in history:
        reached.setdefault(h.to_stage, set()).add(h.lead_id)

    def rate(frm, to):
        f, t = len(reached.get(frm, set())), len(reached.get(to, set()))
        return round(t / f * 100, 1) if f > 0 else None

    conversion_metrics = {
        "contact_to_response": rate("contacted", "responded"),
        "response_to_qualified": rate("responded", "qualified"),
        "qualified_to_appointment": rate("qualified", "appointment"),
        "appointment_to_won": rate("appointment", "won"),
        "overall_conversion_rate": rate("new", "won"),
    }

    # --- Agent metrics (architecture prepared for multi-agent) ---
    agents = db.query(User).all()
    agent_metrics = []
    for agent in agents:
        agent_leads = [l for l in all_leads if l.assigned_agent_id == agent.id]
        activities_count = db.query(func.count(Interaction.id)).filter(Interaction.user_id == agent.id).scalar()
        appointments_count = db.query(func.count(Appointment.id)).join(
            Lead, Appointment.lead_id == Lead.id
        ).filter(Lead.assigned_agent_id == agent.id).scalar()
        won_count = sum(1 for l in agent_leads if resolve_stage(l.status) == "won")
        agent_metrics.append({
            "agent_id": agent.id, "agent_name": agent.full_name or agent.email,
            "leads_count": len(agent_leads), "activities_count": activities_count,
            "appointments_count": appointments_count,
            "conversion_rate_pct": round(won_count / len(agent_leads) * 100, 1) if agent_leads else None,
            "won_count": won_count,
        })

    return {
        "lead_metrics": lead_metrics,
        "follow_up_metrics": follow_up_metrics,
        "conversion_metrics": conversion_metrics,
        "agent_metrics": agent_metrics,
    }

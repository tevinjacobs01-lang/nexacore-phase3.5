"""
Report data builders. Each function returns a pandas DataFrame so the same
data can be rendered as JSON, CSV, Excel, or PDF from one source of truth.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.activity import Activity
from app.models.import_log import ImportLog


def daily_lead_report(db: Session, day: date | None = None) -> pd.DataFrame:
    day = day or date.today()
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)

    rows = (
        db.query(Property)
        .filter(Property.created_at >= start, Property.created_at < end)
        .order_by(Property.lead_score.desc())
        .all()
    )
    return pd.DataFrame([
        {
            "address": p.address, "suburb": p.suburb, "lead_score": p.lead_score,
            "asking_price": float(p.asking_price) if p.asking_price else None,
            "days_on_market": p.days_on_market, "contact_status": p.contact_status,
        }
        for p in rows
    ])


def weekly_performance_report(db: Session, week_start: date | None = None) -> pd.DataFrame:
    week_start = week_start or (date.today() - timedelta(days=date.today().weekday()))
    start = datetime.combine(week_start, datetime.min.time())
    end = start + timedelta(days=7)

    rows = (
        db.query(Activity.activity_type, func.count(Activity.id))
        .filter(Activity.created_at >= start, Activity.created_at < end)
        .group_by(Activity.activity_type)
        .all()
    )
    return pd.DataFrame(rows, columns=["activity_type", "count"])


def monthly_listings_imported_report(db: Session, month: int | None = None, year: int | None = None) -> pd.DataFrame:
    today = date.today()
    month, year = month or today.month, year or today.year
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

    rows = (
        db.query(ImportLog)
        .filter(ImportLog.started_at >= start, ImportLog.started_at < end)
        .order_by(ImportLog.started_at.desc())
        .all()
    )
    return pd.DataFrame([
        {
            "filename": l.filename, "started_at": l.started_at,
            "rows_processed": l.rows_processed, "rows_created": l.rows_created,
            "rows_updated": l.rows_updated, "rows_skipped": l.rows_skipped,
        }
        for l in rows
    ])


def contact_conversion_report(db: Session) -> pd.DataFrame:
    rows = (
        db.query(Property.contact_status, func.count(Property.id))
        .group_by(Property.contact_status)
        .all()
    )
    return pd.DataFrame(rows, columns=["contact_status", "count"])


def lead_score_breakdown_report(db: Session) -> pd.DataFrame:
    buckets = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]
    data = []
    for lo, hi in buckets:
        count = (
            db.query(func.count(Property.id))
            .filter(Property.lead_score >= lo, Property.lead_score < hi)
            .scalar()
        )
        data.append({"score_range": f"{lo}-{hi - 1}", "count": count})
    return pd.DataFrame(data)


REPORTS = {
    "daily-lead": daily_lead_report,
    "weekly-performance": weekly_performance_report,
    "monthly-imports": monthly_listings_imported_report,
    "contact-conversion": contact_conversion_report,
    "score-breakdown": lead_score_breakdown_report,
}

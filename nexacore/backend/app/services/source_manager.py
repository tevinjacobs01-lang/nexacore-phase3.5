"""
Source management (Sprint 18). Seeds a small set of default Source rows so
the Source Management UI has something to show on a fresh install. New
approved sources can be added later purely through the database / admin UI —
no code changes needed as long as a matching collector is registered.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.source import Source

DEFAULT_SOURCES = [
    {
        "name": "CSV / Excel Upload",
        "source_key": "csv_upload",
        "collector_type": "csv_upload",
        "is_enabled": True,
        "disabled_reason": None,
    },
    {
        "name": "Example Licensed Feed API",
        "source_key": "example_licensed_feed",
        "collector_type": "licensed_feed_api",  # no collector registered yet
        "is_enabled": False,
        "disabled_reason": (
            "Placeholder for a future licensed data feed integration. "
            "Disabled until API credentials are provisioned and a matching "
            "collector is implemented and registered."
        ),
    },
    {
        "name": "Generic Property Portal (unapproved)",
        "source_key": "generic_portal_scrape",
        "collector_type": "generic_portal_scrape",  # deliberately unimplemented
        "is_enabled": False,
        "disabled_reason": (
            "No approved API or licensing agreement exists for this source. "
            "Collecting from it would require bypassing robots.txt / anti-bot "
            "protections, which this platform does not do. Left disabled and "
            "undocumented at the collector level until an approved access "
            "path exists."
        ),
    },
]


def seed_default_sources(db: Session) -> None:
    if db.query(Source).count() > 0:
        return
    for entry in DEFAULT_SOURCES:
        db.add(Source(**entry))
    db.commit()

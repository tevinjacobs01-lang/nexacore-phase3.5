from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, properties, dashboard, imports, scoring, activities, notifications, ai, reports,
    sources, scans, listings, leads, contacts, leads_inbox,
    interactions, notes, attachments, tasks, follow_ups, appointments, templates,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(activities.router, prefix="/properties", tags=["activities"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(scoring.router, prefix="/scoring", tags=["scoring"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
api_router.include_router(listings.router, prefix="/listings", tags=["listings"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(
    leads_inbox.router,
    prefix="/leads",
    tags=["leads"]
)
api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(interactions.router, prefix="/interactions", tags=["interactions"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(attachments.router, prefix="/attachments", tags=["attachments"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(follow_ups.router, prefix="/follow-ups", tags=["follow-ups"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])

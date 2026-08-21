from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import SessionLocal
from app.services.scoring_engine import seed_default_rules
from app.services.source_manager import seed_default_sources
import app.collectors  # noqa: F401 — registers built-in collectors

app = FastAPI(title=settings.PROJECT_NAME)


@app.on_event("startup")
def on_startup():
    # Seed default lead-scoring rules and data sources if their tables are
    # empty. Safe to run every time. Wrapped in try/except so a DB that
    # isn't up yet (e.g. first `docker compose up`) doesn't crash the app;
    # migrations should run before this anyway.
    try:
        db = SessionLocal()
        seed_default_rules(db)
        seed_default_sources(db)
        db.close()
    except Exception:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
def health_check():
    return {"status": "ok"}

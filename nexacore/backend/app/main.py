from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import SessionLocal
from app.services.scoring_engine import seed_default_rules
from app.services.source_manager import seed_default_sources
import app.collectors  # noqa: F401 — registers built-in collectors

@asynccontextmanager
async def lifespan(_app: FastAPI):
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

    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

default_cors_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:5177",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
    "http://127.0.0.1:5177",
]
production_frontend_origin = "https://nexacore-property-intelligence.onrender.com"
cors_origins = list(dict.fromkeys((settings.CORS_ORIGINS or default_cors_origins) + [production_frontend_origin]))

lan_origin_regex = (
    r"^(https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?::\d+)?|"
    r"capacitor://localhost)$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=lan_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
def health_check():
    return {"status": "ok"}

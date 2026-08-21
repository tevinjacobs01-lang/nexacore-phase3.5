# NexaCore Property Intelligence

A personal lead intelligence platform for real estate agents. Imports listing data from
approved sources (CSV/Excel now, APIs later), scores opportunities, and helps prioritize
follow-ups.

## Status
This repo is currently a **scaffold**: full project structure, dependency manifests,
database schema, auth skeleton, and a Docker Compose setup are in place. Feature logic
(scoring engine details, importer, dashboard charts, AI assistant, reports) is being
filled in incrementally — see `docs/ROADMAP.md`.

## Stack
- **Frontend:** React + TypeScript + Tailwind CSS
- **Backend:** Python + FastAPI + SQLAlchemy
- **Database:** PostgreSQL
- **Auth:** JWT + bcrypt password hashing
- **Deploy:** Docker + Docker Compose

## Project Structure
```
nexacore/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app entrypoint
│   │   ├── core/               # config, security (JWT, hashing)
│   │   ├── db/                 # SQLAlchemy session/base
│   │   ├── models/              # ORM models (User, Property, LeadScoreRule, Activity, ImportLog)
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── api/v1/endpoints/    # route handlers
│   │   ├── services/           # scoring_engine.py, importer.py (business logic)
│   │   └── tests/
│   ├── alembic/                # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/               # Dashboard, Properties, Login
│   │   ├── components/layout/   # Sidebar, Header
│   │   ├── lib/api.ts           # API client
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── SCHEMA.md
│   ├── API.md
│   └── ROADMAP.md
└── docker-compose.yml
```

## Local Setup

1. Copy `.env.example` to `.env` and fill in secrets.
2. `docker compose up --build`
3. Backend API: http://localhost:8000  (docs at `/docs`)
4. Frontend: http://localhost:5173
5. Postgres: localhost:5432

### Without Docker
Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```
Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Note on data sourcing
This app does not scrape or bypass restrictions on listing websites. Data enters only
via CSV/Excel upload or future approved API integrations.

---

## Phase 2 — Data Collection & Lead Pipeline

Phase 2 adds a generic collector framework, normalization, duplicate detection,
listing history, scan management, source management, and a lead pipeline. See
`docs/PHASE2.md` for the full sprint-by-sprint breakdown.

### Configuration
Same `.env` as Phase 1 — no new required variables. Optional: `ANTHROPIC_API_KEY`
for the AI assistant (unrelated to Phase 2, carried over from Phase 1).

### Database setup
Phase 2 adds new tables (Contact, Source, ScanJob, ListingHistory,
DuplicateMatch, Lead) and one new column on `properties`
(`listing_status`, plus `is_relisted`/`previous_asking_price`/`price_reduced_at`
from Phase 1's scoring work). With Alembic:
```bash
cd backend
alembic revision --autogenerate -m "phase 2: collectors, leads, scan tracking"
alembic upgrade head
```
Without Alembic (dev convenience), `scripts/seed_demo_data.py` calls
`Base.metadata.create_all()` before seeding, which creates any missing tables.

### Running the dashboard
Same as Phase 1 — `docker compose up --build`, then visit the frontend. New
nav items: **Leads** (pipeline board) and **Collection** (sources + scan
history).

### Running scans
1. Go to **Collection** in the sidebar.
2. The CSV/Excel Upload source is enabled by default. Click **Run Scan**,
   choose a file — it runs through the same collector framework every future
   source will use (normalize → validate → dedupe-classify → upsert).
3. Other seeded sources (a placeholder licensed-feed API, a placeholder
   generic portal) are disabled with a documented reason — they have no
   registered collector and are intentionally inert until an approved
   integration exists.

Via API directly:
```bash
curl -X POST http://localhost:8000/api/v1/scans/{source_id}/run \
  -H "Authorization: Bearer <token>" \
  -F "file=@sample_listings.csv"
```

### Adding a collector
1. Create `backend/app/collectors/your_source.py`, subclass `BaseCollector`,
   implement `fetch_raw()` and `normalize()`. Decorate with
   `@CollectorRegistry.register("your_source_key")`.
2. Import it in `backend/app/collectors/__init__.py` so it registers on
   startup.
3. Add a `Source` row (via `/sources/` admin endpoints or directly in DB)
   with `collector_type="your_source_key"` and `is_enabled=true`.
4. **Do not** implement any bypass of CAPTCHA, login walls, anti-bot
   protection, robots.txt, or a site's terms of service. If a source
   requires that, it stays a disabled connector with the reason documented
   on the `Source` row — see Sprint 17/18 notes in `docs/PHASE2.md`.

### Running tests
```bash
cd backend
pip install -r requirements.txt
pytest
```
New Phase 2 test files: `test_normalization.py`, `test_dedupe.py`,
`test_collectors.py`, `test_listing_history.py`, `test_scan_manager.py`,
`test_leads.py`.

### Troubleshooting
- **"No collector registered for 'X'"** — the Source's `collector_type`
  doesn't match any `@CollectorRegistry.register(...)` key, or the
  collector's module isn't imported in `app/collectors/__init__.py`.
- **Scan always fails immediately** — check `Source.is_enabled`; disabled
  sources fail fast by design rather than silently no-op-ing.
- **Duplicate listings showing up as brand-new rows** — this is intentional
  for "likely"/"possible" matches (see Sprint 13); check `/listings/duplicates`
  and resolve them manually. Only "exact" matches auto-merge into the
  existing row.
- **CSV upload via `/scans/{id}/run` returns a config error** — the file
  needs to be sent as multipart form data under the `file` field, same as
  `/imports/upload`.

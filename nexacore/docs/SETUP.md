# Environment Setup

These are the **exact commands** to get NexaCore running locally. This
sandbox cannot execute any of them (no PyPI/npm registry access — the
egress proxy returns `403 host_not_allowed` for `pypi.org` and
`registry.npmjs.org`), so none of the results below have been verified by
actually running them. Run these yourself and report back what breaks.

## Prerequisites
- Python 3.12
- PostgreSQL 16 (or use the provided `docker-compose.yml`, recommended)
- Node.js 20 (for the frontend)

## Option A — Docker Compose (recommended, matches production topology)
```bash
cp .env.example .env
# edit .env: set JWT_SECRET_KEY to a real random value, optionally ANTHROPIC_API_KEY
docker compose up --build
```
Backend: http://localhost:8000/docs · Frontend: http://localhost:5173

## Option B — Manual local setup (needed for direct pytest runs, debugging)

### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Database
Start Postgres (via Docker, standalone, or a local install), then:
```bash
# From backend/, with your .env DATABASE_URL pointing at a real Postgres instance
alembic upgrade head
```
This creates every table from Phases 1–3 from an empty database — see
`docs/MIGRATIONS.md` for what the migration covers and how to verify it.

### Run the backend
```bash
uvicorn app.main:app --reload
```

### Run tests
```bash
# Uses a separate SQLite test database automatically — see docs/TESTING.md.
# Never points at your real Postgres DATABASE_URL.
pytest -v
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Verifying the bootstrap worked
1. `curl http://localhost:8000/health` → `{"status": "ok"}`
2. `pytest -v` → all DB-dependent tests that were previously marked
   NOT EXECUTED should now show real PASS/FAIL results
3. Visit http://localhost:5173, register a user, log in

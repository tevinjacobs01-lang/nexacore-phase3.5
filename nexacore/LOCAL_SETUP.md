# NexaCore — Local Setup

This is the exact sequence to bring the application up on a normal
development machine with real internet access. None of these commands
have been successfully executed end-to-end in the sandbox this repository
was built in — see `PHASE_3_5_STATUS.md` for exactly what was and wasn't
verified.

## Prerequisites
- **Python 3.12** (the venv in this repo was created with 3.12.3)
- **PostgreSQL 16** (or Docker, to run it via `docker-compose.yml`)
- **Node.js 20** and npm
- Internet access to PyPI (`pypi.org`) and the npm registry
  (`registry.npmjs.org`) — this is the one thing the sandbox could not
  provide, and is required for every step below

## 1. Python environment
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
```

## 2. Dependency installation
```bash
python -m pip install -r requirements.txt
```
Installs FastAPI, SQLAlchemy, Alembic, psycopg2-binary, Pydantic,
python-jose + passlib (auth), python-multipart + pandas + openpyxl +
reportlab (file handling), pytest + pytest-cov + httpx (testing), and the
rest of `requirements.txt` — nothing has been added or changed since the
last review.

## 3. Database configuration
Start Postgres (Docker Compose is easiest — see repo root
`docker-compose.yml`), then set `DATABASE_URL` in `backend/.env` (copy
from `.env.example` first):
```bash
cp ../.env.example ../.env
# edit .env: set DATABASE_URL, a real JWT_SECRET_KEY, optionally ANTHROPIC_API_KEY
```

## 4. Alembic migration
```bash
alembic upgrade head
```
This should create all 22 tables from a fresh database using
`alembic/versions/0001_initial_schema.py`. This migration was hand-authored
and cross-validated against every model file (column-by-column, FK-by-FK)
but has **never actually been run against Postgres** — this is genuinely
the first time it will be executed. If it fails, the error message and
which table/column it fails on is the most useful thing to report back.

Sanity check after running it:
```bash
python -c "
from app.db.session import engine
from app.db.base import Base
from sqlalchemy import inspect
inspector = inspect(engine)
tables = set(inspector.get_table_names())
expected = set(Base.metadata.tables.keys())
print('Missing from DB:', expected - tables)
print('Unexpected in DB:', tables - expected)
"
```
Both lines should print empty sets.

## 5. pytest
```bash
pytest -v
```
16 test files, including 6 that specifically target Phase 3 (contact
dedupe, lead stage history, task overdue logic, follow-up due/overdue/
upcoming, appointment status transitions, lead assignment). Tests use an
isolated in-memory SQLite database via `conftest.py` — they will never
touch your real `DATABASE_URL`. This is the first time these will actually
run; until now they were only `py_compile`-checked.

## 6. API startup
```bash
uvicorn app.main:app --reload
```
Check `http://localhost:8000/health` → `{"status": "ok"}`. Interactive
docs at `http://localhost:8000/docs`.

## 7. Smoke test
With the server running (from step 6, in a separate terminal):
```bash
cd backend
source .venv/bin/activate
python scripts/smoke_test_api.py
```
Walks through the full Phase 3 workflow via real HTTP calls: register/login
→ contact → listing → lead → pipeline move (valid + invalid) → stage
history → interaction (+ invalid-id rejection) → note (+ privacy check
with a second user) → task → follow-up → appointment (+ status
transitions) → template render → CRM dashboard → attachment-auth check.
Note: the lead-assignment step is left commented out in the script — there
is no `/users` listing endpoint, so it needs a real user UUID pasted in
manually to run.

## 8. Frontend startup
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173`. Register a user, log in, and the full
Phase 1–3 UI should be reachable from the sidebar: Dashboard, Properties,
Contacts (+ detail), Leads (11-stage pipeline board + detail), Tasks,
Follow-ups, CRM Dashboard, Templates, Collection, AI Assistant, Reports,
Settings.

For a full production-style check:
```bash
npm run build    # runs tsc -b && vite build — first real TypeScript check
```

## Expected verification sequence, end to end
1. `alembic upgrade head` succeeds, DB inspection sanity check prints two
   empty sets
2. `pytest -v` — see how many of the 16 files actually pass; report back
   any failures with their full output
3. `uvicorn` starts without error, `/health` responds
4. `python scripts/smoke_test_api.py` completes all 15 steps (or reports
   exactly which step failed)
5. `npm run build` completes without TypeScript errors
6. Manual click-through of the frontend against the running backend

None of these six have been confirmed to work — this is the actual first
run. Report back whatever breaks and where.

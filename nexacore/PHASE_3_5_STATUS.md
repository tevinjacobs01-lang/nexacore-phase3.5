# Phase 3.5 Integration Hardening — Status

This document is the single source of truth for what is and isn't verified
as of the end of Phase 3.5. Read this before trusting anything in this
repo works. Every claim below is labeled PASS / ERROR / NOT TESTED /
STATICALLY VERIFIED — never "done" or "working" without qualification.

## Why this document exists
Every session building this app ran in a sandbox with **no PyPI or npm
registry access** (`403 host_not_allowed` from the egress proxy, confirmed
directly via `curl`). That means FastAPI, SQLAlchemy, Pydantic, pytest,
and every other dependency were never installed here, and could not be.
Multiple attempts (including a clean venv + real bash shell, eliminating
every other possible cause) all fail at the exact same line:
```
ERROR: Could not find a version that satisfies the requirement fastapi==0.115.0
```
That is a sandbox network policy, not a bug in the code or the setup
instructions.

## What has been completed
- Phases 1–3 (Sprints 1–30): full backend — property/lead data model,
  CSV/Excel import + collector framework, lead scoring, CRM (contacts,
  interactions, notes, attachments, tasks, follow-ups, appointments),
  11-stage sales pipeline with stage history, lead assignment, templates,
  CRM dashboard/analytics.
- Phase 3.5 hardening: reorganized `requirements.txt`, hand-authored and
  cross-validated Alembic migration (22 tables), `conftest.py` with 12
  domain fixtures + isolated test DB, live API smoke-test script, security
  documentation, Deal-entity decision, datetime tech-debt writeup, and the
  full Phase 3 frontend (9 pages + 2 shared components, 20 real API calls,
  zero fake/static data).

## What was STATICALLY VERIFIED (real, scripted checks — not eyeballing)
- **Backend syntax**: 112 files (`app/`, `scripts/`, `conftest.py`,
  Alembic migration + env.py) all compile via `py_compile`. PASS.
- **Frontend syntax**: 34 `.ts`/`.tsx` files, bracket/paren/brace balanced.
  PASS.
- **Migration completeness**: scripted diff of every model's columns
  against the migration's columns, both directions, across all 22 tables
  — zero mismatches. Same for FK targets and unique constraints. PASS.
- **Frontend↔backend route matching**: every API path called from the new
  Phase 3 frontend files (20 calls across 10 files) cross-checked against
  actual registered backend routes — 100% match, zero orphaned calls.
  PASS.
- **Router registration**: all 21 backend endpoint files match all 21
  registered routers exactly. PASS.

## What was ACTUALLY EXECUTED (real runtime, not static)
- Pure-Python logic with no framework dependency: normalization functions,
  duplicate-detection classification, collector retry/error-handling,
  template variable rendering, path-traversal defense in file storage —
  all executed directly in this sandbox with real assertions, multiple
  times across sessions, always passing. This is real verification, but it
  covers business logic only — never anything touching FastAPI,
  SQLAlchemy, or a live HTTP request.
- The dependency-install attempt itself: run three times, including once
  with a clean venv and a genuine bash shell (eliminating shell-artifact
  explanations) — consistently fails at the same PyPI-unreachable line.

## What remains NOT TESTED (sandbox cannot execute)
- **`alembic upgrade head`** against a real database — never run.
- **`pytest`** — never run once. All 16 test files (10 pre-existing + 6
  Phase 3 additions) are written and `py_compile`-clean, but zero of them
  have executed. "STATICALLY VERIFIED" is the correct label for these,
  not PASS.
- **Live server startup** (`uvicorn app.main:app`) — never run.
- **`scripts/smoke_test_api.py`** — never run; requires a live server.
- **`npm install` / `npm run build` / `npm run dev`** — never run; no npm
  registry access either.
- **Any manual click-through of the frontend** — impossible without a
  running backend.

## Known technical debt
- `datetime.utcnow()` used in 19 call sites / 9 files — deprecated as of
  Python 3.12, not refactored (deliberately, per explicit instruction —
  documented in `docs/TECH_DEBT_DATETIME.md`).
- Attachment/note/task/follow-up/appointment access control is
  authenticated-but-unscoped — any logged-in user can see any entity's
  data. Fine for single-tenant use, a real gap before multi-agent
  production. Documented in `docs/ATTACHMENT_AUTHORIZATION.md`.
- No `/users` listing endpoint — blocks a real agent-picker UI for lead
  assignment and blocks fully automating the smoke test's assignment step.
  Deliberately not added (explicit instruction against building it "solely
  to satisfy the smoke test").
- Migration has never been diffed against `Base.metadata.create_all()`'s
  actual output — the real gold-standard schema check, still open.

## Known limitations
- This repository has **never been executed** — not the backend, not the
  frontend, not the tests, not the migration. Everything above the "pure
  Python logic" line is unverified by execution, however carefully it was
  written and cross-checked structurally.
- Structural/static verification (the diffs, the route-matching, the
  syntax checks) catches an entire class of bugs — but it cannot catch
  runtime errors, ORM relationship misconfigurations that only surface at
  query time, dependency version conflicts, or anything that only exists
  when code actually runs.

## This application is NOT production-ready
It has not been proven to install, migrate, start, or serve a single real
request. Phase 3.5's actual job — closing that gap — could not be
completed inside this sandbox. The next real milestone is running
`LOCAL_SETUP.md`'s sequence somewhere with internet access and reporting
back what happens.

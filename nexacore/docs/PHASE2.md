# Phase 2 — Sprint Summary

Continues directly from the Phase 1 codebase. Nothing from Sprints 1–10 was
removed or restructured; Phase 2 only adds new models, services, and endpoints.

## Sprint 11 — Collector Framework
`app/collectors/base.py`: `Listing` (standardized output shape),
`CollectorError`, `CollectorResult`, `BaseCollector` (abstract — subclasses
implement `fetch_raw()` + `normalize()`, get timeout/retry/rate-limit/logging
for free via `run()`), `CollectorRegistry` (decorator-based registration).

## Sprint 12 — Data Normalization
`app/services/normalization.py`: pure functions for price, phone, email,
suburb/city/province, property type, bedroom/bathroom counts, listing dates,
and URLs, plus `validate_listing()`. Verified against real inputs (e.g.
`"R 1 250 000"` → `1250000.0`) during the build.

## Sprint 13 — Duplicate Detection
`app/services/dedupe.py`: `classify_duplicate()` returns exact / likely /
possible / unique with a human-readable reason. Nothing is auto-deleted —
non-exact matches are persisted to `DuplicateMatch` for review via
`GET /listings/duplicates` and resolved via
`POST /listings/duplicates/{id}/resolve`. Exact matches merge directly into
the existing row (same behavior as Phase 1's importer dedupe).

## Sprint 14 — Listing History
`ListingHistory` model + `app/services/listing_history.py::record_change()`.
Tracks previous/new price, description, and status with a timestamp. Wired
into `PATCH /listings/{id}/status`.

## Sprint 15 — Listing Status
Added `Property.listing_status` (new/active/contacted/responded/follow_up/
appointment/converted/not_interested/closed/expired/unknown) — a fuller
lifecycle than Phase 1's simple `contact_status`, which is preserved
unchanged for backward compatibility. Manual changes via
`PATCH /listings/{id}/status`.

## Sprint 16 — Scan Management
`ScanJob` model + `app/services/scan_manager.py::run_scan()`. Records source,
start/end time, duration, discovered/new/updated/duplicate counts, errors,
and status (pending/running/completed/failed/cancelled). Triggered via
`POST /scans/{source_id}/run`, history via `GET /scans/`.

## Sprint 17 — Collector Safety & Reliability
Built into `BaseCollector.run()`: configurable timeout, retry with backoff,
simple rate limiting (`min_seconds_between_requests`), broad exception
capture so one bad record doesn't kill a scan, and `logging` throughout.
Explicitly **not** implemented, by design: any bypass of CAPTCHA, login
walls, anti-bot systems, access controls, or robots.txt. A source needing
that stays a disabled `Source` row with `disabled_reason` documented — see
`app/services/source_manager.py`.

## Sprint 18 — Source Management
`Source` model + `GET /sources/`, `PATCH /sources/{id}` (admin-only
enable/disable). Default seeded sources: CSV/Excel Upload (enabled), and two
disabled placeholders documenting *why* they're disabled (missing
credentials; no approved access path). New sources need zero core-app
changes — register a collector class and add a `Source` row.

## Sprint 19 — Lead Pipeline
`Lead` + `Contact` models. `GET /leads/pipeline` groups leads by stage for a
kanban view (New → Contacted → Responded → Follow-up → Appointment →
Converted, plus Not Interested/Closed side-branches).
`POST /leads/`, `PATCH /leads/{id}` for updates including stage transitions.

## Sprint 20 — Data Collection Dashboard
Extended `/dashboard/summary` with weekly counts, active leads, appointments,
converted leads. New `GET /dashboard/collection` (sources, recent scans,
error counts) and `GET /dashboard/leads` (highest priority, new, follow-ups
due, recently contacted, converted). Frontend: new **Collection** page
(source table + scan history + trigger-scan) and **Leads** page (pipeline
board).

## Data Policy
Per the brief: only official APIs, licensed feeds, public datasets, and
explicitly-permissive sites are valid collector targets. No mechanism in
this codebase is designed to defeat technical protections or access
controls — see Sprint 17 above and `source_manager.py`'s documented
disabled sources for how that's enforced in practice.

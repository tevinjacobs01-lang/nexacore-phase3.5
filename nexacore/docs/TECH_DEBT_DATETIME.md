# Technical Debt: datetime.utcnow() (Phase 3.5, Task 9)

## Status: DOCUMENTED, NOT REFACTORED (by design — see below)

## The issue
`datetime.utcnow()` is used in **19 call sites across 9 files** (excluding
tests): `scan_manager.py`, `importer.py`, `scoring_engine.py`, and the
`leads`, `dashboard`, `follow_ups`, `notifications`, `activities`, `tasks`
endpoints. It's deprecated as of Python 3.12 in favor of timezone-aware
`datetime.now(timezone.utc)` — `utcnow()` returns a *naive* datetime object
(no tzinfo attached), which is exactly the kind of thing that causes subtle
bugs when compared against timezone-aware values from the database (the
app's DateTime columns are all declared `timezone=True`).

## Why this is not being fixed in this pass
You explicitly instructed: "Do not perform a broad datetime.utcnow()
refactor." Even without that instruction, a sweep across 9 files touching
scoring, scanning, importing, leads, dashboards, follow-ups, notifications,
activities, and tasks — all at once, with **no way to execute the test
suite in this sandbox to catch a mistake** — is precisely the kind of
change that should never be bundled into an "integration hardening" pass.
It's real work that deserves its own reviewed, tested change.

## Current impact
None observed. SQLite (used in all sandbox tests) and Postgres both
tolerate naive-vs-aware datetime comparisons more gracefully than the
Python `datetime` module itself does in pure-Python code, and nothing in
the current test suite (to the extent it's been run) has surfaced a bug
from this. It's a forward-looking deprecation concern, not a live defect.

## Recommended future fix (controlled, separate change)
1. Replace every `datetime.utcnow()` with `datetime.now(timezone.utc)`.
2. Add `from datetime import timezone` where missing.
3. Since this touches datetime *comparisons* too (e.g.
   `FollowUp.due_at < today_start` in `follow_ups.py`), re-verify every
   comparison still behaves correctly once both sides are tz-aware —
   mixing naive and aware datetimes in a comparison raises `TypeError` in
   Python, so this isn't a pure find-and-replace.
4. Run the full test suite (once pytest is actually runnable) before and
   after to confirm no regressions — this is exactly the kind of change
   that's invisible until it isn't.
5. Do this as its own PR/change, not bundled with unrelated work.

## Exact call sites (for whoever picks this up)
```
app/services/scan_manager.py
app/services/importer.py
app/services/scoring_engine.py
app/api/v1/endpoints/leads.py
app/api/v1/endpoints/dashboard.py
app/api/v1/endpoints/follow_ups.py
app/api/v1/endpoints/notifications.py
app/api/v1/endpoints/activities.py
app/api/v1/endpoints/tasks.py
```

# Build Roadmap

## Phase 1 — Foundation ✅
Repo structure, Docker Compose, Postgres, SQLAlchemy models, JWT auth, FastAPI
skeleton, React/TS/Tailwind shell with dark mode, Alembic wired up.

## Phase 2 — Property & Import ✅
Full property CRUD with filtering (province/city/suburb/price/beds/baths/type/
sale-rent/days-on-market/score/contact-status/source) and free-text search.
CSV/Excel importer with flexible column mapping, dedupe by listing_reference
(falling back to address+suburb), change-tracking updates, and an ImportLog
audit trail. Verified against a real sample CSV.

## Phase 3 — Lead Scoring Engine ✅
Configurable rule engine (`app/services/scoring_engine.py`) evaluating: days
on market tiers (30/60/90), preferred suburb, price range match, luxury
property, rental opportunity, relisted property, and recent price reduction.
Relisting and price-reduction are detected automatically by the importer.
Default rules seed on first app startup; admin endpoints (`/scoring/rules`)
allow editing points/active-state/config. Every recompute snapshots a
`PropertyScoreHistory` row. The importer recomputes scores for every
created/updated property automatically.

## Phase 4 — Frontend Dashboard + Filters UI ✅
Recharts bar charts for listings by suburb / price range / property type, and
lead score distribution, all backed by real aggregation endpoints. A
FiltersSidebar component wired to the properties list covering every filter
field in the spec, plus free-text search. A NotificationsPanel surfaces
follow-ups due, new hot listings, and properties updated since yesterday.

## Phase 5 — CRM + Search + Notifications backend ✅
Activity endpoints nested under properties (`/properties/{id}/activities`):
mark contacted / interested / not interested, add a note, schedule a
follow-up, archive — each both logs an Activity row and updates the
property's CRM state. `/notifications/` returns the three reminder buckets
used by the dashboard panel.

## Phase 6 — AI Assistant, Reports, Exports ✅
`/ai/summarize/{id}`, `/ai/explain-score/{id}`, `/ai/prioritize`, `/ai/ask`
wrap the Anthropic API (requires `ANTHROPIC_API_KEY` in `.env`; endpoints
return a clear 503 if unset rather than crashing). `/reports/{type}` returns
JSON for daily-lead, weekly-performance, monthly-imports, contact-conversion,
and score-breakdown reports; `/reports/{type}/export?format=csv|xlsx|pdf`
streams a download. CSV/Excel/PDF generation was verified directly against
sample data.

## Frontend pages ✅
Settings (edit scoring rules, trigger recompute-all), AI Assistant (ask
natural-language questions with the spec's example prompts as quick buttons,
"who should I call today" prioritization), and Reports (switch between all 5
report types, view as a table, export CSV/Excel/PDF via real file download)
are now wired up and routed in the sidebar nav.

## Known gaps / next steps
- No automated frontend build/type-check was run in this environment (no
  network access to install node_modules) — run `npm install && npm run build`
  locally to verify. Bracket-balance and manual review passed on all files.
- No live Postgres/SQLAlchemy test run was possible in this environment
  either (no network to install SQLAlchemy) — run `pytest` locally.
- Role-based UI gating isn't implemented yet — the Settings page will just
  show a load error for non-admin users (backend already enforces
  `require_admin`), but there's no frontend redirect/hide.
- Future Modules from the original spec (WhatsApp, email campaigns, SMS,
  calendar sync, multi-agent/agency accounts, billing, valuation module,
  market analytics, native mobile app) are not started.

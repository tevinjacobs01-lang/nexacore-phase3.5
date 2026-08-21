# API Overview

Base path: `/api/v1`

## Auth
- `POST /auth/register`
- `POST /auth/login` — returns `{ access_token, token_type }`

## Properties
- `GET /properties/` — list with filters: `q`, `province`, `city`, `suburb`,
  `property_type`, `listing_type`, `contact_status`, `listing_source`,
  `min_price`/`max_price`, `min_rental`/`max_rental`, `bedrooms`, `bathrooms`,
  `min_days_on_market`/`max_days_on_market`, `min_score`/`max_score`,
  `sort_by`, `sort_dir`, `skip`, `limit`
- `GET /properties/count`
- `POST /properties/`
- `GET /properties/{id}`
- `PATCH /properties/{id}`
- `DELETE /properties/{id}`

## Activities (CRM)
- `GET /properties/{id}/activities`
- `POST /properties/{id}/activities` — `activity_type` one of: contacted,
  interested, not_interested, note, follow_up_scheduled, archived

## Dashboard
- `GET /dashboard/summary`
- `GET /dashboard/charts/by-suburb`
- `GET /dashboard/charts/by-property-type`
- `GET /dashboard/charts/by-price-range`
- `GET /dashboard/charts/score-distribution`

## Notifications
- `GET /notifications/` — follow_ups_due, new_hot_listings, updated_since_yesterday

## Imports
- `POST /imports/upload` — multipart file upload (.csv/.xls/.xlsx)
- `GET /imports/` — history
- `GET /imports/{id}` — detail with per-row errors

## Scoring (admin)
- `GET /scoring/rules`
- `POST /scoring/rules`
- `PATCH /scoring/rules/{id}`
- `POST /scoring/recompute` — recompute all properties
- `POST /scoring/recompute/{property_id}`

## AI Assistant (requires ANTHROPIC_API_KEY)
- `POST /ai/summarize/{property_id}`
- `POST /ai/explain-score/{property_id}`
- `POST /ai/prioritize`
- `POST /ai/ask` — `{ question: str }`

## Reports
- `GET /reports/{report_type}` — JSON. Types: daily-lead, weekly-performance,
  monthly-imports, contact-conversion, score-breakdown
- `GET /reports/{report_type}/export?format=csv|xlsx|pdf`

## Sources (Phase 2)
- `GET /sources/` — list all data sources
- `PATCH /sources/{id}` — admin only; enable/disable, set config

## Scans (Phase 2)
- `GET /scans/` — scan history, optional `source_id` filter
- `POST /scans/{source_id}/run` — trigger a scan; attach `file` (multipart)
  for file-based collectors like csv_upload

## Listings (Phase 2)
- `GET /listings/{id}/history` — price/description/status change history
- `PATCH /listings/{id}/status` — manual lifecycle status change
- `GET /listings/duplicates` — flagged potential duplicates, optional
  `resolved` filter
- `POST /listings/duplicates/{id}/resolve` — mark a duplicate match reviewed

## Leads (Phase 2)
- `GET /leads/` — list, optional `status`/`priority` filters
- `GET /leads/pipeline` — leads grouped by pipeline stage
- `POST /leads/` — create a lead from a property (+ optional contact)
- `PATCH /leads/{id}` — update status/priority/assignment/follow-up/notes

Interactive docs auto-generate at `/docs` once the backend is running.


## Contacts (added during Phase 2 verification)
- `GET /contacts/` — list
- `POST /contacts/` — create
- `GET /contacts/{id}`

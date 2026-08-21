# Database Schema (Phase 1)

## users
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| email | varchar(255) unique | |
| hashed_password | varchar(255) | bcrypt |
| full_name | varchar(255) | nullable |
| role | varchar(50) | "agent" \| "admin" |
| is_active | boolean | |
| created_at | timestamptz | |

## properties
All fields from the spec's Property Database section: internal id, listing reference,
address/suburb/city/province/postal code, lat/lng, sale-or-rent, property type,
bedrooms/bathrooms/garages, floor/stand size, asking price, monthly rental, listing
date, last updated, days on market, listing source/url, agent name/contact/email,
notes — plus:
- **CRM fields:** contact_status, lead_score, follow_up_date, last_contacted_at
- **Scoring signals** (set automatically by the importer): is_relisted,
  previous_asking_price, price_reduced_at — feed the "Relisted Property" and
  "Recent Price Reduction" scoring rules.

See `backend/app/models/property.py` for exact column types.

## lead_score_rules
Configurable scoring rules (rule_key, points, is_active, config) editable from the
admin settings page.

## property_score_history
Point-in-time score snapshots with a breakdown per rule, for audit/trend purposes.

## activities
CRM activity log per property: contacted / interested / not_interested / note /
follow_up_scheduled / archived, tied to a user.

## import_logs
One row per CSV/Excel import run: counts (processed/created/updated/skipped),
captured errors, timestamps.

## Phase 2 additions

### contacts
Normalized agent/seller contact (name, phone, email), reusable across
listings and leads.

### sources
A data source a collector can pull from: name, source_key, collector_type
(matches `CollectorRegistry`), is_enabled, disabled_reason, config (JSON),
last_successful_scan_at, last_error, listings_collected_count.

### scan_jobs
One run of a collector against a source: status (pending/running/completed/
failed/cancelled), started/finished timestamps, duration, discovered/new/
updated/duplicate counts, error_count, errors.

### listing_history
Change audit trail per property: previous/new price, previous/new
description, previous/new status, changed_at.

### duplicate_matches
Flagged (never auto-merged) potential duplicate between two properties:
match_type (exact/likely/possible), match_reason, resolved.

### leads
Actionable lead linked to a property (+ optional contact): status
(new/contacted/responded/follow_up/appointment/converted/not_interested/
closed), priority (low/medium/high), assigned_agent_id, last_contacted_at,
next_follow_up, notes.

### properties (new columns)
`listing_status` — fuller lifecycle status (new/active/contacted/responded/
follow_up/appointment/converted/not_interested/closed/expired/unknown),
distinct from the existing `contact_status` quick-action field.

Diagrams / ERD can be generated later with `alembic` + a tool like `eralchemy` once
migrations exist.

# Deal Entity Decision (Phase 3.5, Task 8)

## Situation
Sprint 23's spec lists notes/attachments as attachable to "listings,
contacts, leads, or deals." No Phase 1-3 sprint ever specified a Deal
model's fields, and none was created. Before this fix, `entity_type="deal"`
was silently accepted as valid input but got zero existence validation —
inconsistent with `listing`/`contact`/`lead`, which are checked against
real tables.

## Decision: Option A — reject "deal" until a Deal model exists
`NOTE_ENTITY_TYPES` and `ATTACHMENT_ENTITY_TYPES` no longer include
`"deal"`. A request with `entity_type="deal"` now gets a clean
`400 Bad Request` ("entity_type must be one of ['contact', 'lead',
'listing']") instead of being silently accepted with no integrity check.

## Why this option over documenting deal as intentionally unchecked
- Consistency: every other entity type is validated. An unvalidated
  exception is a footgun — a typo'd or garbage `entity_id` for a "deal"
  note would persist forever with no way to detect it.
  the spec's own Sprint 3 verification instructions explicitly warn against
  this class of gap ("invalid entity IDs return appropriate errors").
- Reversibility: this is trivially undone the moment a real Deal model is
  added — just add it back to the two sets and wire it into
  `_get_entity_model_map()` in `notes.py` (and the equivalent spot in
  `attachments.py` if the same pattern is added there).
- No functionality is lost: nothing in Phases 1-3 ever created or consumed
  deal-attached notes/attachments, so no existing behavior depends on
  `entity_type="deal"` working.

## What would change if a Deal model is added later
1. Add `app/models/deal.py` with whatever fields Phase 4+ specifies.
2. Add `"deal"` back to `NOTE_ENTITY_TYPES` / `ATTACHMENT_ENTITY_TYPES`.
3. Add `"deal": Deal` to `_get_entity_model_map()` in both `notes.py` and
   `attachments.py` (both now use the identical pattern — see Bugs Fixed
   in the Phase 3.5 report; `attachments.py` previously had zero
   entity-existence validation for any type, fixed alongside this decision).

# Attachment Authorization Model (Phase 3.5, Task 7)

## Current model: authenticated-but-not-scoped

Every attachment endpoint requires a valid JWT (`get_current_user`) — there
is **no unauthenticated access anywhere**. Beyond that:

| Action | Who can do it today |
|---|---|
| Upload an attachment to any listing/contact/lead | Any authenticated user |
| List attachments for any entity | Any authenticated user |
| Download any attachment | Any authenticated user |
| Delete an attachment | Only the user who uploaded it (`uploaded_by == current_user.id`) |

This is the **same authorization model used everywhere else in the app**
(Phase 1-3): any authenticated agent can see any property, any lead, any
contact. There is currently no concept of "this lead belongs to Agent X, so
only Agent X (or an admin) can see its attachments." `Lead.assigned_agent_id`
exists (Sprint 28) but nothing enforces it as an access boundary — it's
informational/ownership metadata, not a security gate.

## Why this is acceptable today, and why it won't be for production
This is fine for a **single-tenant, internal tool** where every user is a
trusted member of the same small team — which is exactly the "do not
require multi-user SaaS functionality yet" scope Sprint 28 was explicitly
built to. It is **not** fine the moment this becomes a real multi-agent
deployment where Agent A's clients' private documents (IDs, signed
mandates, financial info) shouldn't be visible to Agent B by default.

## TECHNICAL DEBT — required before multi-agent production rollout
**Entity-level attachment authorization is not implemented.** Before
deploying this to more than one mutually-trusting user:

1. Decide the access model: assigned-agent-only? Admin-override? Team-based
   sharing? (Product decision, not made here.)
2. Add an authorization check to `download_attachment`,
   `list_attachments`, and `upload_attachment` in `attachments.py` that
   resolves the parent entity (listing/contact/lead) and checks the
   requesting user against its ownership/assignment, not just "is logged
   in."
3. Same consideration applies to `notes.py` (private notes are already
   author-scoped, but *non-private* notes are visible to any authenticated
   user regardless of entity ownership) and arguably to `interactions.py`,
   `tasks.py`, `follow_ups.py`, `appointments.py` — all currently
   authenticated-but-unscoped in the same way.
4. This is a cross-cutting concern (affects most Phase 3 endpoints, not
   just attachments) and deserves its own design pass rather than a
   piecemeal fix — flagging it here as the single source of truth for that
   future work.

## Explicitly NOT done in this pass
Per your instruction, no multi-tenant authorization was implemented here.
This document exists so the gap is visible and intentional, not
accidentally discovered in production.

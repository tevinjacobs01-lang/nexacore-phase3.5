"""enforce leads.contact_id NOT NULL (contact required on every lead)

Revision ID: 0006_leads_contact_required
Revises: 0005_communications_foundation
Create Date: 2026-08-23

The NexaCore Realty Intelligence lead redesign made Contact mandatory on
every Lead and Property optional. Revision 0408a0bdd383 flipped
property_id to nullable but never enforced NOT NULL on contact_id,
leaving migration-built databases divergent from the ORM models
(app/models/lead.py declares contact_id as nullable=False).

SAFETY: if any existing leads have a NULL contact_id, this migration
ABORTS without changing anything rather than silently deleting or
re-pointing rows. Resolve those rows manually (link each to a contact,
or remove genuinely orphaned leads), then re-run `alembic upgrade head`.
This migration deliberately performs no destructive data operations.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0006_leads_contact_required"
down_revision: Union[str, Sequence[str], None] = "0005_communications_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    null_contact_rows = bind.execute(
        sa.text("SELECT COUNT(*) FROM leads WHERE contact_id IS NULL")
    ).scalar_one()

    if null_contact_rows:
        raise RuntimeError(
            f"Cannot enforce leads.contact_id NOT NULL: {null_contact_rows} lead "
            "row(s) have no contact. Link each one to a contact, or delete "
            "genuinely orphaned leads, then re-run 'alembic upgrade head'. "
            "This migration does not delete or reassign data automatically."
        )

    op.alter_column(
        "leads",
        "contact_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "leads",
        "contact_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

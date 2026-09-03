"""add contact association to captures"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0014_capture_contact"
down_revision = "0013_captures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("captures", sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_captures_contact_id", "captures", "contacts", ["contact_id"], ["id"])
    op.create_index("ix_captures_contact_id", "captures", ["contact_id"])


def downgrade() -> None:
    op.drop_index("ix_captures_contact_id", table_name="captures")
    op.drop_constraint("fk_captures_contact_id", "captures", type_="foreignkey")
    op.drop_column("captures", "contact_id")
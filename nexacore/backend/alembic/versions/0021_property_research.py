"""Persist non-destructive Copilot property research history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0021_property_research"
down_revision = "0020_hunting_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "property_research",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("original_url", sa.String(length=1000), nullable=True),
        sa.Column("source_status", sa.String(length=50), nullable=False, server_default="not_requested"),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="nexacore_record"),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_property_research_property_id", "property_research", ["property_id"])
    op.create_index("ix_property_research_lead_id", "property_research", ["lead_id"])
    op.create_index("ix_property_research_requested_by", "property_research", ["requested_by"])


def downgrade() -> None:
    op.drop_table("property_research")

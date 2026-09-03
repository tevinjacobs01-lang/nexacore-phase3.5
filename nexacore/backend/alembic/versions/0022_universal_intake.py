"""Add lightweight auditable universal intake submissions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0022_universal_intake"
down_revision = "0021_property_research"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("intake_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("input_type", sa.String(length=20), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("source_domain", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="review_required"),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column("extracted_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=True),
        sa.Column("capture_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("captures.id"), nullable=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("discovery_opportunities.id"), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_intake_submissions_user_id", "intake_submissions", ["user_id"])
    op.create_index("ix_intake_submissions_source_url", "intake_submissions", ["source_url"])
    op.create_index("ix_intake_submissions_property_id", "intake_submissions", ["property_id"])
    op.create_index("ix_intake_submissions_capture_id", "intake_submissions", ["capture_id"])
    op.create_index("ix_intake_submissions_opportunity_id", "intake_submissions", ["opportunity_id"])
    op.create_index("ix_intake_submissions_lead_id", "intake_submissions", ["lead_id"])

def downgrade() -> None:
    op.drop_table("intake_submissions")

"""add user-owned screenshot capture evidence"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_captures"
down_revision = "0012_webhook_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "captures",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="review_required"),
        sa.Column("extraction_method", sa.String(length=50), nullable=False, server_default="manual_review"),
        sa.Column("extracted_data", sa.JSON(), nullable=False),
        sa.Column("extraction_notes", sa.Text(), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["discovery_opportunities.id"]),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_captures_user_id", "captures", ["user_id"])
    op.create_index("ix_captures_property_id", "captures", ["property_id"])
    op.create_index("ix_captures_opportunity_id", "captures", ["opportunity_id"])


def downgrade() -> None:
    op.drop_index("ix_captures_opportunity_id", table_name="captures")
    op.drop_index("ix_captures_property_id", table_name="captures")
    op.drop_index("ix_captures_user_id", table_name="captures")
    op.drop_table("captures")
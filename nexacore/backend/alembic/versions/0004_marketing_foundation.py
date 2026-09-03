"""Add authorization-gated marketing records and asset metadata."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_marketing_foundation"
down_revision = "0003_discovery_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "marketing_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=False, unique=True),
        sa.Column("authorized_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("authorization_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("authorization_evidence", sa.Text()),
        sa.Column("marketing_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("authorization_status IN ('pending', 'authorized', 'revoked')", name="ck_marketing_authorization_status"),
        sa.CheckConstraint("marketing_status IN ('draft', 'active', 'paused', 'completed')", name="ck_marketing_status"),
    )
    op.create_table(
        "marketing_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("marketing_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("marketing_records.id"), nullable=False),
        sa.Column("media_url", sa.String(2000), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("caption", sa.Text()),
        sa.Column("source", sa.String(255)),
        sa.Column("authorization_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("marketing_usage_permitted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("asset_type IN ('image', 'video')", name="ck_marketing_asset_type"),
    )
    op.create_index("ix_marketing_assets_marketing_record_id", "marketing_assets", ["marketing_record_id"])


def downgrade():
    op.drop_index("ix_marketing_assets_marketing_record_id", table_name="marketing_assets")
    op.drop_table("marketing_assets")
    op.drop_table("marketing_records")

"""Add configurable non-destructive lead hunting profile."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0020_hunting_profile"
down_revision = "0019_user_verification_approval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hunting_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, server_default="Default property lead profile"),
        sa.Column("target_locations", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("property_types", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("intent_types", sa.Text(), nullable=False, server_default='["sale", "rent"]'),
        sa.Column("advertiser_types", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("priority_signals", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("minimum_display_confidence", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("hunting_profiles")
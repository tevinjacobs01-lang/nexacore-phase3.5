"""add persisted source scheduling state"""

from alembic import op
import sqlalchemy as sa


revision = "0007_source_scheduling"
down_revision = "a77e176f0679"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("sources", sa.Column("schedule_interval_minutes", sa.Integer(), nullable=False, server_default="60"))
    op.add_column("sources", sa.Column("next_scan_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sources", sa.Column("last_scan_started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("sources", "last_scan_started_at")
    op.drop_column("sources", "next_scan_at")
    op.drop_column("sources", "schedule_interval_minutes")
    op.drop_column("sources", "schedule_enabled")
"""add persisted source health counters"""

from alembic import op
import sqlalchemy as sa


revision = "0008_source_health"
down_revision = "0007_source_scheduling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("last_failed_scan_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sources", sa.Column("total_scans", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("sources", sa.Column("successful_scans", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("sources", sa.Column("failed_scans", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("sources", sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("sources", sa.Column("opportunities_generated", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("sources", "opportunities_generated")
    op.drop_column("sources", "records_processed")
    op.drop_column("sources", "failed_scans")
    op.drop_column("sources", "successful_scans")
    op.drop_column("sources", "total_scans")
    op.drop_column("sources", "last_failed_scan_at")
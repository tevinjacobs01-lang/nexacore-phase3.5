"""Link intelligence-generated tasks to their originating opportunity."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0018_task_opportunity_link"
down_revision = "0017_opportunity_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_tasks_opportunity_id", "tasks", "discovery_opportunities", ["opportunity_id"], ["id"])
    op.create_index("ix_tasks_opportunity_id", "tasks", ["opportunity_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_opportunity_id", table_name="tasks")
    op.drop_constraint("fk_tasks_opportunity_id", "tasks", type_="foreignkey")
    op.drop_column("tasks", "opportunity_id")
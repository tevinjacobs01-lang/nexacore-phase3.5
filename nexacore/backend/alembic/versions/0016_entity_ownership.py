"""add ownership metadata for agent-level authorization"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0016_entity_ownership"
down_revision = "0015_object_storage_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("properties", "contacts", "tasks", "appointments"):
        op.add_column(table, sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(f"fk_{table}_created_by", table, "users", ["created_by"], ["id"])
        op.create_index(f"ix_{table}_created_by", table, ["created_by"])


def downgrade() -> None:
    for table in ("appointments", "tasks", "contacts", "properties"):
        op.drop_index(f"ix_{table}_created_by", table_name=table)
        op.drop_constraint(f"fk_{table}_created_by", table, type_="foreignkey")
        op.drop_column(table, "created_by")
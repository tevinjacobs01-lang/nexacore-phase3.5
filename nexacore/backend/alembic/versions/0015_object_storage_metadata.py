"""add durable object storage metadata to uploads"""

from alembic import op
import sqlalchemy as sa


revision = "0015_object_storage_metadata"
down_revision = "0014_capture_contact"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("attachments", "captures"):
        op.add_column(table, sa.Column("object_key", sa.String(length=1000), nullable=True))
        op.add_column(table, sa.Column("storage_provider", sa.String(length=30), nullable=False, server_default="local"))
        op.add_column(table, sa.Column("storage_bucket", sa.String(length=255), nullable=True))
        op.create_index(f"ix_{table}_object_key", table, ["object_key"])


def downgrade() -> None:
    for table in ("captures", "attachments"):
        op.drop_index(f"ix_{table}_object_key", table_name=table)
        op.drop_column(table, "storage_bucket")
        op.drop_column(table, "storage_provider")
        op.drop_column(table, "object_key")
"""add user-scoped tenant rental requirements"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_tenant_requirements"
down_revision = "0008_source_health"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suburb", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("province", sa.String(length=255), nullable=True),
        sa.Column("min_budget", sa.Numeric(14, 2), nullable=True),
        sa.Column("max_budget", sa.Numeric(14, 2), nullable=True),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("parking", sa.Integer(), nullable=True),
        sa.Column("property_type", sa.String(length=100), nullable=True),
        sa.Column("move_in_date", sa.Date(), nullable=True),
        sa.Column("other_requirements", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_requirements_user_id", "tenant_requirements", ["user_id"])
    op.create_index("ix_tenant_requirements_contact_id", "tenant_requirements", ["contact_id"])


def downgrade() -> None:
    op.drop_index("ix_tenant_requirements_contact_id", table_name="tenant_requirements")
    op.drop_index("ix_tenant_requirements_user_id", table_name="tenant_requirements")
    op.drop_table("tenant_requirements")
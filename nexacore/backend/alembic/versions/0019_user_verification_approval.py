"""Add email verification and owner approval lifecycle to users."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0019_user_verification_approval"
down_revision = "0018_task_opportunity_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("approval_status", sa.String(length=20), nullable=False, server_default="approved"))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("verification_token", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("verification_token_expiry", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("rejection_reason", sa.String(length=500), nullable=True))
    op.create_index("ix_users_verification_token", "users", ["verification_token"])
    op.create_foreign_key("fk_users_approved_by", "users", "users", ["approved_by"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_users_approved_by", "users", type_="foreignkey")
    op.drop_index("ix_users_verification_token", table_name="users")
    for column in ("rejection_reason", "approved_at", "approved_by", "verification_token_expiry", "verification_token", "email_verified", "approval_status"):
        op.drop_column("users", column)
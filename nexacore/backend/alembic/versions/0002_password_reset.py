"""Add password reset token fields."""
from alembic import op
import sqlalchemy as sa


revision = "0002_password_reset"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("reset_token", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("reset_token_expiry", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_reset_token", "users", ["reset_token"])


def downgrade():
    op.drop_index("ix_users_reset_token", table_name="users")
    op.drop_column("users", "reset_token_expiry")
    op.drop_column("users", "reset_token")
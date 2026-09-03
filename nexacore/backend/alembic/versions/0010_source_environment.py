"""classify sources by runtime environment"""

from alembic import op
import sqlalchemy as sa


revision = "0010_source_environment"
down_revision = "0009_tenant_requirements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("environment", sa.String(length=20), nullable=False, server_default="development"))
    op.create_check_constraint("ck_sources_environment", "sources", "environment IN ('development', 'test', 'production')")


def downgrade() -> None:
    op.drop_constraint("ck_sources_environment", "sources", type_="check")
    op.drop_column("sources", "environment")
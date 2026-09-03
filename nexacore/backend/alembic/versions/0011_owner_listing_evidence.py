"""add explicit owner listing evidence"""

from alembic import op
import sqlalchemy as sa


revision = "0011_owner_listing_evidence"
down_revision = "0010_source_environment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("properties", sa.Column("seller_type", sa.String(length=20), nullable=True))
    op.add_column("properties", sa.Column("is_owner_listed", sa.Boolean(), nullable=True))
    op.create_check_constraint(
        "ck_properties_seller_type",
        "properties",
        "seller_type IS NULL OR seller_type IN ('owner', 'agent', 'agency', 'developer', 'unknown')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_properties_seller_type", "properties", type_="check")
    op.drop_column("properties", "is_owner_listed")
    op.drop_column("properties", "seller_type")
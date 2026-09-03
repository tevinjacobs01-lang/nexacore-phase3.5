"""Persist explainable opportunity intelligence fields."""
from alembic import op
import sqlalchemy as sa


revision = "0017_opportunity_intelligence"
down_revision = "0016_entity_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("discovery_opportunities", sa.Column("opportunity_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("discovery_opportunities", sa.Column("signal_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("discovery_opportunities", sa.Column("data_confidence", sa.String(length=20), nullable=False, server_default="unknown"))
    op.add_column("discovery_opportunities", sa.Column("intelligence_reasons", sa.Text(), nullable=True))
    op.add_column("discovery_opportunities", sa.Column("recommended_action", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("discovery_opportunities", "recommended_action")
    op.drop_column("discovery_opportunities", "intelligence_reasons")
    op.drop_column("discovery_opportunities", "data_confidence")
    op.drop_column("discovery_opportunities", "signal_score")
    op.drop_column("discovery_opportunities", "opportunity_score")
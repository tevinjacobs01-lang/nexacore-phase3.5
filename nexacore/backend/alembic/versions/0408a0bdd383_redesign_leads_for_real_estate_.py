"""redesign leads for real estate categories

Revision ID: 0408a0bdd383
Revises: 0002_password_reset
Create Date: 2026-08-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0408a0bdd383"
down_revision: Union[str, Sequence[str], None] = "0002_password_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column(
            "lead_type",
            sa.String(length=30),
            nullable=False,
            server_default="seller",
        ),
    )

    op.add_column(
        "leads",
        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
            server_default="manual",
        ),
    )

    op.add_column(
        "leads",
        sa.Column(
            "lead_score",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.alter_column(
        "leads",
        "property_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "leads",
        "property_id",
        existing_type=sa.UUID(),
        nullable=False,
    )

    op.drop_column("leads", "lead_score")
    op.drop_column("leads", "source")
    op.drop_column("leads", "lead_type")
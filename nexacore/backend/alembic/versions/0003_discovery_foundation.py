"""Add discovery provenance, lifecycle, qualification, searches, and events."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_discovery_foundation"
down_revision = "0408a0bdd383"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "listing_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("source_listing_id", sa.String(255), nullable=True),
        sa.Column("canonical_url", sa.String(1000), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("discovery_method", sa.String(100), nullable=True),
        sa.Column("source_confidence", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_company", sa.String(255), nullable=True),
        sa.Column("contact_agency", sa.String(255), nullable=True),
        sa.Column("contact_confidence", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("lifecycle_status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.Text, nullable=True),
        sa.UniqueConstraint("source_id", "source_listing_id", name="uq_observation_source_listing"),
        sa.CheckConstraint("lifecycle_status IN ('new', 'active', 'price_changed', 'removed', 'expired', 'relisted')", name="ck_observation_lifecycle_status"),
        sa.CheckConstraint("source_confidence IN ('high', 'medium', 'low', 'unknown')", name="ck_observation_source_confidence"),
        sa.CheckConstraint("contact_confidence IN ('high', 'medium', 'low', 'unknown')", name="ck_observation_contact_confidence"),
    )
    for name, columns in (
        ("ix_observation_source_id", ["source_id"]),
        ("ix_observation_property_id", ["property_id"]),
        ("ix_observation_source_listing_id", ["source_listing_id"]),
        ("ix_observation_canonical_url", ["canonical_url"]),
    ):
        op.create_index(name, "listing_observations", columns)

    op.create_table(
        "discovery_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=False, unique=True),
        sa.Column("latest_observation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listing_observations.id"), nullable=True),
        sa.Column("classification", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("qualification_status", sa.String(30), nullable=False, server_default="unreviewed"),
        sa.Column("qualification_reason", sa.Text, nullable=True),
        sa.Column("discovery_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("classification IN ('seller', 'landlord', 'unknown')", name="ck_opportunity_classification"),
        sa.CheckConstraint("qualification_status IN ('unreviewed', 'qualified', 'not_qualified', 'review_required')", name="ck_opportunity_qualification_status"),
    )
    op.create_index("ix_opportunity_property_id", "discovery_opportunities", ["property_id"])
    op.create_index("ix_opportunity_latest_observation_id", "discovery_opportunities", ["latest_observation_id"])
    op.create_index("ix_opportunity_reviewed_by", "discovery_opportunities", ["reviewed_by"])

    op.create_table(
        "saved_searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("suburbs", sa.Text, nullable=True),
        sa.Column("property_type", sa.String(100), nullable=True),
        sa.Column("min_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("listing_type", sa.String(20), nullable=True),
        sa.Column("bedrooms", sa.Integer, nullable=True),
        sa.Column("bathrooms", sa.Integer, nullable=True),
        sa.Column("minimum_score", sa.Integer, nullable=True),
        sa.Column("lead_type", sa.String(20), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("lead_type IN ('seller', 'landlord')", name="ck_saved_search_lead_type"),
    )
    op.create_index("ix_saved_searches_user_id", "saved_searches", ["user_id"])

    op.create_table(
        "discovery_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("discovery_opportunities.id"), nullable=True),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listing_observations.id"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", sa.Text, nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for name, columns in (
        ("ix_discovery_events_user_id", ["user_id"]),
        ("ix_discovery_events_property_id", ["property_id"]),
        ("ix_discovery_events_opportunity_id", ["opportunity_id"]),
        ("ix_discovery_events_observation_id", ["observation_id"]),
        ("ix_discovery_events_event_type", ["event_type"]),
    ):
        op.create_index(name, "discovery_events", columns)


def downgrade():
    for name in (
        "ix_discovery_events_event_type", "ix_discovery_events_observation_id",
        "ix_discovery_events_opportunity_id", "ix_discovery_events_property_id",
        "ix_discovery_events_user_id",
    ):
        op.drop_index(name, table_name="discovery_events")
    op.drop_table("discovery_events")
    op.drop_index("ix_saved_searches_user_id", table_name="saved_searches")
    op.drop_table("saved_searches")
    for name in ("ix_opportunity_reviewed_by", "ix_opportunity_latest_observation_id", "ix_opportunity_property_id"):
        op.drop_index(name, table_name="discovery_opportunities")
    op.drop_table("discovery_opportunities")
    for name in (
        "ix_observation_canonical_url", "ix_observation_source_listing_id",
        "ix_observation_property_id", "ix_observation_source_id",
    ):
        op.drop_index(name, table_name="listing_observations")
    op.drop_table("listing_observations")

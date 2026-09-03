"""Add provider-neutral communication foundation.

Revision ID: 0005_communications_foundation
Revises: 0004_marketing_foundation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_communications_foundation"
down_revision = "0004_marketing_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("communication_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False), sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(255)), sa.Column("external_identifier", sa.String(255)),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"), sa.Column("sync_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_communication_accounts_user_id", "communication_accounts", ["user_id"])
    op.create_table("conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id")), sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id")), sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id")), sa.Column("communication_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("communication_accounts.id")),
        sa.Column("channel", sa.String(30), nullable=False), sa.Column("external_thread_id", sa.String(255)), sa.Column("subject", sa.String(500)), sa.Column("status", sa.String(30), nullable=False, server_default="open"), sa.Column("last_message_at", sa.DateTime(timezone=True)), sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("user_id", "contact_id", "lead_id", "property_id", "communication_account_id", "external_thread_id", "last_message_at"): op.create_index(f"ix_conversations_{column}", "conversations", [column])
    op.create_table("communication_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=False), sa.Column("communication_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("communication_accounts.id")), sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id")), sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id")), sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id")), sa.Column("direction", sa.String(20), nullable=False), sa.Column("channel", sa.String(30), nullable=False), sa.Column("provider_message_id", sa.String(255)), sa.Column("provider_thread_id", sa.String(255)), sa.Column("sender_name", sa.String(255)), sa.Column("sender_address", sa.String(255)), sa.Column("recipient_address", sa.String(1000)), sa.Column("subject", sa.String(500)), sa.Column("body_text", sa.Text()), sa.Column("body_preview", sa.String(500)), sa.Column("received_at", sa.DateTime(timezone=True)), sa.Column("sent_at", sa.DateTime(timezone=True)), sa.Column("status", sa.String(30), nullable=False, server_default="sent"), sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("has_attachments", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("metadata", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("conversation_id", "communication_account_id", "contact_id", "lead_id", "property_id", "provider_message_id", "provider_thread_id"): op.create_index(f"ix_communication_messages_{column}", "communication_messages", [column])
    op.create_table("communication_attachments", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("communication_messages.id"), nullable=False), sa.Column("provider_attachment_id", sa.String(255)), sa.Column("filename", sa.String(500), nullable=False), sa.Column("mime_type", sa.String(255)), sa.Column("size_bytes", sa.Integer()), sa.Column("storage_key", sa.String(1000)), sa.Column("external_url", sa.String(2000)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_communication_attachments_message_id", "communication_attachments", ["message_id"])


def downgrade():
    op.drop_index("ix_communication_attachments_message_id", table_name="communication_attachments"); op.drop_table("communication_attachments")
    for column in ("conversation_id", "communication_account_id", "contact_id", "lead_id", "property_id", "provider_message_id", "provider_thread_id"): op.drop_index(f"ix_communication_messages_{column}", table_name="communication_messages")
    op.drop_table("communication_messages")
    for column in ("user_id", "contact_id", "lead_id", "property_id", "communication_account_id", "external_thread_id", "last_message_at"): op.drop_index(f"ix_conversations_{column}", table_name="conversations")
    op.drop_table("conversations"); op.drop_index("ix_communication_accounts_user_id", table_name="communication_accounts"); op.drop_table("communication_accounts")

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base

# Import all models so Alembic knows about all tables.
from app.models.user import User
from app.models.property import Property
from app.models.lead_score import LeadScoreRule, PropertyScoreHistory
from app.models.activity import Activity
from app.models.import_log import ImportLog
from app.models.contact import Contact
from app.models.source import Source
from app.models.scan_job import ScanJob
from app.models.listing_history import ListingHistory
from app.models.duplicate_match import DuplicateMatch
from app.models.lead import Lead
from app.models.contact_property import ContactProperty
from app.models.interaction import Interaction
from app.models.note import Note
from app.models.attachment import Attachment
from app.models.task import Task
from app.models.follow_up import FollowUp
from app.models.appointment import Appointment
from app.models.lead_stage_history import LeadStageHistory
from app.models.assignment import Assignment
from app.models.communication_template import CommunicationTemplate

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = settings.DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    configuration = config.get_section(config.config_ini_section) or {}

    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
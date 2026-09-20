import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.core.config import settings
from src.database.base import Base

# Import every model module here so its table gets registered on
# Base.metadata before autogenerate compares it against the database.
from src.database.models import (
    achievement,
    anime,
    app_integration_settings,
    auth,
    bounty,
    card,
    game,
    game_archive,
    game_checklist_item,
    game_field_change,
    game_file_item,
    game_profile,
    game_profile_stat_snapshot,
    inbox_item,
    media_extras,
    media_item,
    movies,
    notification,
    password_reset,
    tv_show,
    user,
    user_appearance_settings,
    user_invitation,
    user_preferences,
    user_scan_settings,
)
from src.database.models import set as set_model  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL scripts without a live DB connection (rarely used)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Connect using the async engine and run migrations against it."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.database.base import Base

from importlib import import_module


# Import every model module here so its table gets registered on
# Base.metadata before autogenerate compares it against the database.
# import app.database.models in the run_migrations_online function instead to avoid global side effects.


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


    # Explicitly load model modules within the async context to prevent global import side effects
    model_modules = ["app.database.models.game", "app.database.models.developer", "app.database.models.achievement"]
    for module_path in model_modules:
        try:
            import_module(module_path)
            print(f"Successfully loaded metadata from {module_path}")
        except Exception as e:
            # Log the failure but do not crash the migration process
            print(f"WARNING: Could not load models from {module_path}. It may contain circular dependencies or failed imports. Error: {e}")

async def run_migrations_online() -> None:
    """Connect using the async engine and run migrations against it."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # === Model Loading Enhancement ===
    # This block manually loads model metadata to prevent global import errors during Alembic's setup phase.
    model_modules = ["app.database.models.game", "app.database.models.developer", "app.database.models.achievement"]
    for module_path in model_modules:
        try:
            # Using exec to simulate import without affecting global state too much, or just using __import__
            module = __import__(module_path, fromlist=[''])
            print(f"Successfully loaded metadata from {module_path}")
        except Exception as e:
            print(f"WARNING: Could not load models from {module_path}. Skipping for now. Error: {e}")
    # ===============================

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
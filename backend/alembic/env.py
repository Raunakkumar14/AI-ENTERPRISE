"""
backend/alembic/env.py
───────────────────────
Alembic migration environment for async SQLAlchemy.

Key responsibilities:
  1. Load the DATABASE_URL from app settings (respects the .env file).
  2. Import all ORM models so that `alembic revision --autogenerate`
     can detect schema changes.
  3. Support both offline (SQL dump) and online (live DB) migration modes.

How to use:
    cd backend                               # must be run from backend/ dir
    alembic revision --autogenerate -m "init"   # create a migration
    alembic upgrade head                         # apply all pending migrations
    alembic downgrade -1                         # roll back one migration
    alembic current                              # show current DB version
    alembic history                              # show migration history
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# ── Make `app` importable ─────────────────────────────────────────────────────
# Add the backend/ directory to sys.path so that `from app.xxx import yyy`
# works when Alembic is run from inside backend/ or from the project root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Import all models so autogenerate can detect them ─────────────────────────
# Add new model imports here as you create them:
#   from app.models.document import Document   # noqa: F401
from app.models import Base  # noqa: F401  ← imports all models into metadata

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy metadata used for autogenerate comparisons
target_metadata = Base.metadata

# ── Override DB URL with the value from app settings ─────────────────────────
# This ensures we always use the same URL as the running application.
from app.config import settings as app_settings  # noqa: E402

config.set_main_option(
    "sqlalchemy.url",
    app_settings.DATABASE_URL.replace("%", "%%"),
)


# ── Offline mode ─────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Emit SQL to stdout without a live database connection.
    Useful for generating migration SQL to review or run manually.

    Run with:  alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render CREATE EXTENSION for pgvector if needed
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (async) ───────────────────────────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        # Compare server defaults so Alembic detects DEFAULT value changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations in the online mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # don't keep connections open during migration
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online (live DB) migrations."""
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

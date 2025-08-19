# alembic/env.py
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.engine import Connection
from alembic import context

# --- Make 'src' imports work when running `uv run alembic ...`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Import your metadata
from fms_client.data.db import Base  # DeclarativeBase
# If you didn’t centralize Base, you can also do:
# from fms_client.data.mfr_record import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic about your model metadata for autogenerate
target_metadata = Base.metadata

# Read DB URL from env var if present, otherwise fallback to alembic.ini
db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Optional: ensure Alembic version table lives in the 'mfr' schema
# Only do this if your app uses schema 'mfr' (we do).
VERSION_TABLE_SCHEMA = "mfr"
VERSION_TABLE_NAME = "alembic_version"


# ... keep your imports and sys.path setup ...

from fms_client.data.db import Base
from alembic import context
from sqlalchemy import engine_from_config, pool, text

config = context.config
target_metadata = Base.metadata

def _set_search_path(conn):
    conn.execute(text("SET search_path TO mfr, public"))

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        version_table="alembic_version",
        version_table_schema="mfr",   # << pin to mfr
        include_schemas=True,         # << important when using explicit schema
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        _set_search_path(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            version_table="alembic_version",
            version_table_schema="mfr",  # << pin to mfr
            include_schemas=True,        # << important when using explicit schema
        )
        with context.begin_transaction():
            context.run_migrations()

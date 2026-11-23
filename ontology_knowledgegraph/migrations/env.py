from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from pathlib import Path
import os
from dotenv import load_dotenv

config = context.config
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
database_url = os.getenv("PG_URL") or os.getenv("DATABASE_URL")
if database_url:
    # Escape percent signs because ConfigParser treats them as interpolation markers.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
else:
    raise RuntimeError("Set PG_URL (or DATABASE_URL) in ontology_knowledgegraph/.env")

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

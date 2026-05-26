from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
import app.models  # noqa: F401, E402 - register all ORM models on Base.metadata
from app.models.base import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def _connect_args_for_url(url: str) -> dict[str, object]:
    """Supabase requires TLS; ensure sslmode when URL omits it (common with dashboard copy-paste)."""
    lower = url.lower()
    if ("supabase.co" in lower or "pooler.supabase.com" in lower) and "sslmode" not in lower:
        return {"sslmode": "require"}
    return {}


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = settings.database_url
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=_connect_args_for_url(url),
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

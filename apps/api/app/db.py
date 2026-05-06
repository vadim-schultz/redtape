from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def _connect_args_for_url(url: str) -> dict[str, object]:
    """Supabase requires TLS; ensure sslmode when URL omits it."""
    lower = url.lower()
    if (
        "supabase.co" in lower or "pooler.supabase.com" in lower
    ) and "sslmode" not in lower:
        return {"sslmode": "require"}
    return {}


def _create_engine() -> Engine:
    url = settings.database_url
    return create_engine(
        url,
        echo=False,
        future=True,
        connect_args=_connect_args_for_url(url),
    )


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def provide_session() -> Generator[Session, None, None]:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

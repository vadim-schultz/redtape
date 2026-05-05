from __future__ import annotations

from typing import Any

from litestar import Request, get
from litestar.response import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.locale import SupportedLocale, UITranslation


@get("/health", sync_to_thread=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@get("/api/v1/locales", sync_to_thread=True)
def list_locales(session: Session) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(SupportedLocale)
        .where(SupportedLocale.enabled.is_(True))
        .order_by(SupportedLocale.code)
    ).all()
    return [
        {
            "code": row.code,
            "name_native": row.name_native,
            "name_english": row.name_english,
            "flag_emoji": row.flag_emoji,
            "enabled": row.enabled,
            "completeness_pct": row.completeness_pct,
        }
        for row in rows
    ]


@get("/api/v1/translations", sync_to_thread=True)
def translations_bundle(session: Session, request: Request) -> Response:
    locale = getattr(request.state, "locale", "de")
    rows = session.execute(
        select(UITranslation.key, UITranslation.value).where(UITranslation.locale == locale)
    ).all()
    bundle = {row.key: row.value for row in rows}
    payload: dict[str, Any] = {"locale": locale, "translations": bundle}
    return Response(
        payload,
        media_type="application/json",
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
        },
    )

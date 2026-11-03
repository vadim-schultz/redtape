"""Characterization for `/api/v1/locales` and `/api/v1/translations`, moved out of `routes.py` (D3)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from app.main import create_app
from app.models.locale import SupportedLocale, UITranslation
from app.schema.locale.read import LocaleRead, TranslationBundle
from litestar import Litestar
from litestar.testing import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

LOCALES = "/api/v1/locales"
TRANSLATIONS = "/api/v1/translations"


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    for code in ("de", "en", "fr"):
        db_session.execute(sa.delete(SupportedLocale).where(SupportedLocale.code == code))
        db_session.execute(sa.delete(UITranslation).where(UITranslation.locale == code))
    db_session.add_all(
        [
            SupportedLocale(
                code="de",
                name_native="Deutsch",
                name_english="German",
                flag_emoji="\U0001f1e9\U0001f1ea",
                enabled=True,
                completeness_pct=100.0,
            ),
            SupportedLocale(
                code="en",
                name_native="English",
                name_english="English",
                flag_emoji="\U0001f1ec\U0001f1e7",
                enabled=True,
                completeness_pct=80.0,
            ),
            SupportedLocale(
                code="fr",
                name_native="Francais",
                name_english="French",
                flag_emoji=None,
                enabled=False,
                completeness_pct=0.0,
            ),
            UITranslation(key="greeting", locale="de", value="Hallo"),
        ]
    )
    db_session.flush()
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


def test_locales_lists_enabled_locales_sorted_by_code_with_all_fields(client: TestClient[Litestar]) -> None:
    body = client.get(LOCALES).json()

    assert body == [
        {
            "code": "de",
            "name_native": "Deutsch",
            "name_english": "German",
            "flag_emoji": "\U0001f1e9\U0001f1ea",
            "enabled": True,
            "completeness_pct": 100.0,
        },
        {
            "code": "en",
            "name_native": "English",
            "name_english": "English",
            "flag_emoji": "\U0001f1ec\U0001f1e7",
            "enabled": True,
            "completeness_pct": 80.0,
        },
    ]


def test_translations_returns_bundle_for_request_locale_with_cache_header(client: TestClient[Litestar]) -> None:
    response = client.get(TRANSLATIONS, params={"locale": "de"})

    assert response.json() == {"locale": "de", "translations": {"greeting": "Hallo"}}
    assert response.headers["Cache-Control"] == "public, max-age=3600, stale-while-revalidate=86400"


def test_translations_for_unsupported_locale_falls_back_to_de(client: TestClient[Litestar]) -> None:
    response = client.get(TRANSLATIONS, params={"locale": "xx"})

    assert response.json() == {"locale": "de", "translations": {"greeting": "Hallo"}}


def test_translations_for_locale_without_rows_returns_empty_bundle(client: TestClient[Litestar]) -> None:
    response = client.get(TRANSLATIONS, params={"locale": "en"})

    assert response.json() == {"locale": "en", "translations": {}}


def test_locale_read_rejects_missing_fields() -> None:
    with pytest.raises(ValidationError):
        LocaleRead.model_validate({"code": "de"})


def test_translation_bundle_shape() -> None:
    bundle = TranslationBundle(locale="de", translations={"greeting": "Hallo"})

    assert bundle.model_dump() == {"locale": "de", "translations": {"greeting": "Hallo"}}

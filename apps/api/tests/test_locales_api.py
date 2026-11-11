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
    for code in ("de", "en", "fr", "tr"):
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
            UITranslation(key="farewell", locale="de", value="Tschuess"),
            UITranslation(key="greeting", locale="en", value="Hello"),
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
            "completeness_pct": 50.0,
        },
    ]


def test_translations_returns_bundle_for_request_locale_with_cache_header(client: TestClient[Litestar]) -> None:
    response = client.get(TRANSLATIONS, params={"locale": "de"})

    assert response.json() == {"locale": "de", "translations": {"greeting": "Hallo", "farewell": "Tschuess"}}
    assert response.headers["Cache-Control"] == "public, max-age=3600, stale-while-revalidate=86400"


def test_translations_for_unsupported_locale_falls_back_to_de(client: TestClient[Litestar]) -> None:
    response = client.get(TRANSLATIONS, params={"locale": "xx"})

    assert response.json() == {"locale": "de", "translations": {"greeting": "Hallo", "farewell": "Tschuess"}}


def test_translations_for_a_locale_with_rows_returns_only_its_own_rows(client: TestClient[Litestar]) -> None:
    response = client.get(TRANSLATIONS, params={"locale": "en"})

    assert response.json() == {"locale": "en", "translations": {"greeting": "Hello"}}


def test_locale_read_rejects_missing_fields() -> None:
    with pytest.raises(ValidationError):
        LocaleRead.model_validate({"code": "de"})


def test_translation_bundle_shape() -> None:
    bundle = TranslationBundle(locale="de", translations={"greeting": "Hallo"})

    assert bundle.model_dump() == {"locale": "de", "translations": {"greeting": "Hallo"}}


def test_completeness_is_computed_from_ui_translation_coverage(
    client: TestClient[Litestar], db_session: Session
) -> None:
    db_session.add(UITranslation(key="farewell", locale="en", value="Goodbye"))
    db_session.flush()

    by_code = {row["code"]: row["completeness_pct"] for row in client.get(LOCALES).json()}

    assert by_code == {"de": 100.0, "en": 100.0}


def test_completeness_ignores_keys_the_source_locale_lacks_and_never_exceeds_100(
    client: TestClient[Litestar], db_session: Session
) -> None:
    db_session.add_all(
        [
            UITranslation(key="farewell", locale="en", value="Goodbye"),
            UITranslation(key="extra", locale="en", value="Extra"),
        ]
    )
    db_session.flush()

    by_code = {row["code"]: row["completeness_pct"] for row in client.get(LOCALES).json()}

    assert by_code["en"] == 100.0


def test_a_locale_without_rows_has_zero_completeness_and_a_disabled_one_is_not_listed(
    client: TestClient[Litestar], db_session: Session
) -> None:
    db_session.add(SupportedLocale(code="tr", name_native="Turkce", name_english="Turkish", enabled=False))
    db_session.execute(sa.delete(UITranslation).where(UITranslation.locale == "en"))
    db_session.flush()

    by_code = {row["code"]: row["completeness_pct"] for row in client.get(LOCALES).json()}

    assert by_code == {"de": 100.0, "en": 0.0}


def test_completeness_is_zero_for_every_locale_when_the_source_has_no_keys(
    client: TestClient[Litestar], db_session: Session
) -> None:
    db_session.execute(sa.delete(UITranslation))
    db_session.flush()

    by_code = {row["code"]: row["completeness_pct"] for row in client.get(LOCALES).json()}

    assert by_code == {"de": 0.0, "en": 0.0}

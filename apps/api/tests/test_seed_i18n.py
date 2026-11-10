from __future__ import annotations

import json
from pathlib import Path

import pytest
import scripts.seed_i18n as seed_i18n
import sqlalchemy as sa
from app.models.locale import SupportedLocale, UITranslation
from app.shared.locale import SUPPORTED_LOCALES
from scripts.seed_i18n import _flatten_dict, _load_nested_json, seed_supported_locales, seed_ui_translations
from sqlalchemy.orm import Session

TRANSLATIONS_DIR = Path(seed_i18n.__file__).resolve().parent / "seed_data" / "translations"


def _flat_keys(locale: str) -> dict[str, str]:
    return _flatten_dict(_load_nested_json(TRANSLATIONS_DIR / f"{locale}.json"))


def _translation_count(session: Session) -> int:
    return session.execute(sa.select(sa.func.count()).select_from(UITranslation)).scalar_one()


def test_flatten_joins_nested_keys_with_dots_and_stringifies_leaves() -> None:
    flat = _flatten_dict({"a": {"b": {"c": "x"}, "d": 2}, "e": True})

    assert flat == {"a.b.c": "x", "a.d": "2", "e": "True"}


def test_load_nested_json_rejects_an_array_root(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    with pytest.raises(TypeError, match="Expected object at root"):
        _load_nested_json(path)


def _enabled_by_code(session: Session) -> dict[str, bool]:
    rows = session.execute(sa.select(SupportedLocale.code, SupportedLocale.enabled)).all()
    return {code: enabled for code, enabled in rows}


def test_seed_supported_locales_creates_every_supported_locale_and_is_idempotent(db_session: Session) -> None:
    seed_supported_locales(db_session)
    seed_supported_locales(db_session)

    codes = db_session.execute(sa.select(SupportedLocale.code)).scalars().all()
    assert sorted(codes) == sorted(spec.code for spec in SUPPORTED_LOCALES)
    assert sorted(codes) == ["de", "en", "pl", "ro", "ru", "tr", "uk"]


def test_seed_adds_the_new_locales_disabled_and_keeps_de_and_en_enabled(db_session: Session) -> None:
    seed_supported_locales(db_session)

    assert _enabled_by_code(db_session) == {
        "de": True,
        "en": True,
        "tr": False,
        "ru": False,
        "uk": False,
        "pl": False,
        "ro": False,
    }


def test_seed_keeps_an_enabled_flag_flipped_by_an_operator(db_session: Session) -> None:
    seed_supported_locales(db_session)
    db_session.execute(sa.update(SupportedLocale).where(SupportedLocale.code == "tr").values(enabled=True))
    db_session.execute(sa.update(SupportedLocale).where(SupportedLocale.code == "en").values(enabled=False))

    seed_supported_locales(db_session)

    enabled = _enabled_by_code(db_session)
    assert enabled["tr"] is True
    assert enabled["en"] is False


def test_seed_supported_locales_restores_a_changed_name_native_on_rerun(db_session: Session) -> None:
    seed_supported_locales(db_session)
    db_session.execute(sa.update(SupportedLocale).where(SupportedLocale.code == "de").values(name_native="Changed"))

    seed_supported_locales(db_session)

    name = db_session.execute(sa.select(SupportedLocale.name_native).where(SupportedLocale.code == "de")).scalar_one()
    assert name == "Deutsch"


def test_seed_ui_translations_stores_every_key_of_both_seed_files(db_session: Session) -> None:
    seed_ui_translations(db_session)

    expected = len(_flat_keys("de")) + len(_flat_keys("en"))
    assert _translation_count(db_session) == expected


def test_seed_ui_translations_rerun_adds_no_rows_but_overwrites_an_edited_value(db_session: Session) -> None:
    seed_ui_translations(db_session)
    first_count = _translation_count(db_session)
    key, value = next(iter(_flat_keys("de").items()))
    db_session.execute(
        sa.update(UITranslation).where(UITranslation.key == key, UITranslation.locale == "de").values(value="edited")
    )

    seed_ui_translations(db_session)

    assert _translation_count(db_session) == first_count
    stored = db_session.execute(
        sa.select(UITranslation.value).where(UITranslation.key == key, UITranslation.locale == "de")
    ).scalar_one()
    assert stored == value


def test_de_and_en_seed_files_have_the_same_keys() -> None:
    assert set(_flat_keys("de")) ^ set(_flat_keys("en")) == set()


def test_a_translation_file_for_an_unknown_locale_fails_loudly_and_writes_nothing(
    db_session: Session, tmp_path: Path
) -> None:
    (tmp_path / "de.json").write_text(json.dumps({"a": "x"}), encoding="utf-8")
    (tmp_path / "fr.json").write_text(json.dumps({"a": "y"}), encoding="utf-8")

    with pytest.raises(ValueError, match=r"fr\.json.*SUPPORTED_LOCALES"):
        seed_ui_translations(db_session, root=tmp_path)

    assert _translation_count(db_session) == 0


def test_a_translation_file_for_a_supported_locale_is_seeded_from_a_custom_root(
    db_session: Session, tmp_path: Path
) -> None:
    (tmp_path / "tr.json").write_text(json.dumps({"a": {"b": "x"}}), encoding="utf-8")

    seed_ui_translations(db_session, root=tmp_path)

    stored = db_session.execute(sa.select(UITranslation.key, UITranslation.locale, UITranslation.value)).all()
    assert [tuple(row) for row in stored] == [("a.b", "tr", "x")]

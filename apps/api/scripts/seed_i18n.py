"""Seed the supported locales and the UI translation catalogue from seed_data/translations."""

from __future__ import annotations

import json
from pathlib import Path

from app.db import SessionLocal
from app.models.locale import SupportedLocale, UITranslation
from app.shared.locale import SUPPORTED_LOCALE_CODES, SUPPORTED_LOCALES
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

TRANSLATIONS_ROOT = Path(__file__).resolve().parent / "seed_data" / "translations"


def _flatten_dict(data: dict[str, object], parent: str = "", sep: str = ".") -> dict[str, str]:
    items: dict[str, str] = {}
    for key, value in data.items():
        path = f"{parent}{sep}{key}" if parent else key
        if isinstance(value, dict):
            nested = value  # type: dict[str, object]
            items.update(_flatten_dict(nested, parent=path, sep=sep))
        else:
            items[path] = str(value)
    return items


def _load_nested_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        payload: object = json.load(handle)
    if not isinstance(payload, dict):
        msg = f"Expected object at root: {path}"
        raise TypeError(msg)
    return payload


def seed_supported_locales(session: Session) -> None:
    """Upsert one row per entry of ``SUPPORTED_LOCALES``.

    New rows take ``enabled`` from the entry (only de and en start enabled). A rerun refreshes the
    names and flag but never ``enabled``, so an operator's flip survives the seed that runs on every boot.
    """
    for spec in SUPPORTED_LOCALES:
        ins = pg_insert(SupportedLocale).values(
            code=spec.code,
            name_native=spec.name_native,
            name_english=spec.name_english,
            flag_emoji=spec.flag_emoji,
            enabled=spec.enabled_by_default,
        )
        stmt = ins.on_conflict_do_update(
            index_elements=[SupportedLocale.code],
            set_={
                "name_native": ins.excluded.name_native,
                "name_english": ins.excluded.name_english,
                "flag_emoji": ins.excluded.flag_emoji,
            },
        )
        session.execute(stmt)


def _translation_files(root: Path) -> list[Path]:
    """Return the translation files under ``root``; raise when one names a locale outside ``SUPPORTED_LOCALES``."""
    paths = sorted(root.glob("*.json"))
    unknown = [path.name for path in paths if path.stem not in SUPPORTED_LOCALE_CODES]
    if unknown:
        msg = f"translation file(s) {', '.join(unknown)} name a locale not in SUPPORTED_LOCALES"
        raise ValueError(msg)
    return paths


def _upsert_translations(session: Session, locale: str, flat: dict[str, str]) -> None:
    """Upsert every ``key -> value`` pair for ``locale``, overwriting an existing value in place."""
    for key, value in flat.items():
        ins = pg_insert(UITranslation).values(key=key, locale=locale, value=value, context=None)
        session.execute(
            ins.on_conflict_do_update(
                index_elements=[UITranslation.key, UITranslation.locale],
                set_={"value": ins.excluded.value, "updated_at": func.now()},
            )
        )


def seed_ui_translations(session: Session, root: Path = TRANSLATIONS_ROOT) -> None:
    """Upsert every translation file under ``root``, one locale per file named by its stem.

    Nested keys are flattened with dots. Every file is checked against ``SUPPORTED_LOCALES`` before
    any row is written, so an unknown locale fails loudly instead of being skipped. Rerunning
    overwrites existing values in place, so the catalogue always matches the JSON files.
    """
    for path in _translation_files(root):
        _upsert_translations(session, path.stem, _flatten_dict(_load_nested_json(path)))


def main() -> None:
    """Run both i18n seeds in one transaction and commit them together."""
    with SessionLocal() as session:
        seed_supported_locales(session)
        seed_ui_translations(session)
        session.commit()
    print("i18n seed complete (supported_locale + ui_translation).")


if __name__ == "__main__":
    main()

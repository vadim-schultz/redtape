"""Seed the supported locales and the UI translation catalogue from seed_data/translations."""

from __future__ import annotations

import json
from pathlib import Path

from app.db import SessionLocal
from app.models.locale import SupportedLocale, UITranslation
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import func


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
    """Upsert the German and English locale rows, enabling them and refreshing their names on rerun."""
    rows: list[dict[str, object]] = [
        {
            "code": "de",
            "name_native": "Deutsch",
            "name_english": "German",
            "flag_emoji": "🇩🇪",
            "enabled": True,
            "completeness_pct": 100.0,
        },
        {
            "code": "en",
            "name_native": "English",
            "name_english": "English",
            "flag_emoji": "🇬🇧",
            "enabled": True,
            "completeness_pct": 100.0,
        },
    ]
    for row in rows:
        ins = pg_insert(SupportedLocale).values(**row)
        stmt = ins.on_conflict_do_update(
            index_elements=[SupportedLocale.code],
            set_={
                "name_native": ins.excluded.name_native,
                "name_english": ins.excluded.name_english,
                "flag_emoji": ins.excluded.flag_emoji,
                "enabled": ins.excluded.enabled,
                "completeness_pct": ins.excluded.completeness_pct,
            },
        )
        session.execute(stmt)


def seed_ui_translations(session: Session) -> None:
    """Upsert every translation file, one locale per file named by its stem, flattening nested keys with dots.

    Rerunning overwrites existing values in place, so the catalogue always matches the JSON files.
    """
    root = Path(__file__).resolve().parent / "seed_data" / "translations"
    for path in sorted(root.glob("*.json")):
        locale = path.stem
        nested = _load_nested_json(path)
        flat = _flatten_dict(nested)
        for key, value in flat.items():
            ins = pg_insert(UITranslation).values(
                key=key,
                locale=locale,
                value=value,
                context=None,
            )
            stmt = ins.on_conflict_do_update(
                index_elements=[UITranslation.key, UITranslation.locale],
                set_={
                    "value": ins.excluded.value,
                    "updated_at": func.now(),
                },
            )
            session.execute(stmt)


def main() -> None:
    """Run both i18n seeds in one transaction and commit them together."""
    with SessionLocal() as session:
        seed_supported_locales(session)
        seed_ui_translations(session)
        session.commit()
    print("i18n seed complete (supported_locale + ui_translation).")


if __name__ == "__main__":
    main()

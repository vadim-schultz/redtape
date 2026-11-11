"""Guarded locale enablement: a locale is enabled only with a recorded review and 100% coverage (search-first C11)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
import sqlalchemy as sa
from app.models.locale import SupportedLocale
from pydantic import ValidationError
from scripts.enable_locale import EnableRefusedError, enable_locale
from scripts.seed_data.review_manifest import LocaleReview, ReviewManifest, load_review_manifest
from scripts.seed_i18n import seed_supported_locales, seed_ui_translations
from sqlalchemy.orm import Session

REVIEWED = LocaleReview(
    status="reviewed", reviewed_by="I. Petrov", reviewed_on=date(2026, 12, 2), model="m", command_version="1"
)
MACHINE = LocaleReview(status="machine", model="m", command_version="1")


def _seed(session: Session, tmp_path: Path, ru: dict[str, object]) -> None:
    (tmp_path / "de.json").write_text(json.dumps({"a": "x", "b": {"c": "y", "d": "z"}}), encoding="utf-8")
    (tmp_path / "ru.json").write_text(json.dumps(ru), encoding="utf-8")
    seed_supported_locales(session)
    seed_ui_translations(session, root=tmp_path)


def _enabled(session: Session, code: str) -> bool:
    return session.execute(sa.select(SupportedLocale.enabled).where(SupportedLocale.code == code)).scalar_one()


def test_a_reviewed_and_complete_locale_is_enabled(db_session: Session, tmp_path: Path) -> None:
    """enable_locale · enables a reviewed, complete locale and reports its completeness."""
    _seed(db_session, tmp_path, {"a": "а", "b": {"c": "б", "d": "в"}})

    completeness = enable_locale(db_session, "ru", ReviewManifest(locales={"ru": REVIEWED}))

    assert completeness == 100.0 and _enabled(db_session, "ru") is True


def test_a_machine_only_locale_is_refused_with_the_reason_and_stays_disabled(
    db_session: Session, tmp_path: Path
) -> None:
    """enable_locale · refuses a machine-only locale: the reason names the status and the missing review."""
    _seed(db_session, tmp_path, {"a": "а", "b": {"c": "б", "d": "в"}})

    with pytest.raises(EnableRefusedError, match="machine.*review"):
        enable_locale(db_session, "ru", ReviewManifest(locales={"ru": MACHINE}))

    assert _enabled(db_session, "ru") is False


def test_an_incomplete_locale_is_refused_with_its_completeness(db_session: Session, tmp_path: Path) -> None:
    """enable_locale · refuses a reviewed locale that lacks keys: the reason gives the completeness."""
    _seed(db_session, tmp_path, {"a": "а", "b": {"c": "б"}})

    with pytest.raises(EnableRefusedError, match=r"completeness 66\.7"):
        enable_locale(db_session, "ru", ReviewManifest(locales={"ru": REVIEWED}))

    assert _enabled(db_session, "ru") is False


@pytest.mark.parametrize("code", ["pl", "fr"])
def test_a_locale_without_a_manifest_entry_or_outside_the_supported_list_is_refused(
    db_session: Session, tmp_path: Path, code: str
) -> None:
    """enable_locale · no entry in review.json, or a code that is not supported, is refused and changes nothing."""
    _seed(db_session, tmp_path, {"a": "а", "b": {"c": "б", "d": "в"}})

    with pytest.raises(EnableRefusedError):
        enable_locale(db_session, code, ReviewManifest(locales={"ru": REVIEWED}))

    assert _enabled(db_session, "ru") is False


def test_the_manifest_loads_from_review_json_and_a_reviewed_entry_needs_who_and_when(tmp_path: Path) -> None:
    """enable_locale · the manifest is review.json; `reviewed` without reviewer and date does not load."""
    path = tmp_path / "review.json"
    path.write_text(
        json.dumps({"locales": {"ru": {"status": "reviewed", "model": "m", "command_version": "1"}}}), encoding="utf-8"
    )

    with pytest.raises(ValidationError, match="reviewed_by"):
        load_review_manifest(path)
    assert load_review_manifest(tmp_path / "missing.json").locales == {}


def test_the_committed_manifest_loads_and_names_only_supported_locales() -> None:
    """enable_locale · the review.json in the repository is valid and every locale in it is supported."""
    from app.shared.locale import SUPPORTED_LOCALE_CODES

    assert set(load_review_manifest().locales) <= SUPPORTED_LOCALE_CODES


@pytest.mark.parametrize("code", ["tr", "ru", "uk", "pl", "ro"])
def test_no_committed_locale_can_be_enabled_until_a_native_speaker_review_is_recorded(
    db_session: Session, code: str
) -> None:
    """enable_locale · with the committed files and manifest every target locale is complete but refused as machine text."""
    seed_supported_locales(db_session)
    seed_ui_translations(db_session)

    with pytest.raises(EnableRefusedError, match="machine.*review"):
        enable_locale(db_session, code, load_review_manifest())

    assert _enabled(db_session, code) is False

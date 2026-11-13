"""Layering and configuration guards for the snapshot enqueue (chapter 09)."""

from __future__ import annotations

from pathlib import Path

from app.features.translation.enqueue import TranslationEnqueuer
from app.features.translation.snapshot_enqueue import SnapshotEnqueuer
from app.models.snapshot_translation import SnapshotTranslationTask
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from snapshot_machine_support import SHA_A, add_snapshot
from test_architecture import APP_ROOT, module_imports
from test_discovery_admin_api import _catalogue


def _translation_repository_hits(path: Path, source: str | None = None) -> list[tuple[int, str]]:
    """Every import in ``path`` of a translation module whose name is a repository."""
    return [
        (lineno, dotted)
        for lineno, dotted in module_imports(path, source=source)
        if dotted.startswith("app.features.translation.") and "repository" in dotted
    ]


def _discovery_repository_hits(path: Path) -> list[tuple[int, str]]:
    """Every import in ``path`` of a discovery repository module."""
    return [
        (lineno, dotted)
        for lineno, dotted in module_imports(path)
        if dotted.startswith("app.features.discovery.repository")
    ]


def test_no_discovery_module_imports_a_translation_repository() -> None:
    discovery = sorted((APP_ROOT / "features" / "discovery").rglob("*.py"))
    offenders = [
        (path.relative_to(APP_ROOT).as_posix(), lineno, dotted)
        for path in discovery
        for lineno, dotted in _translation_repository_hits(path)
    ]

    assert offenders == []


def test_the_import_check_flags_a_discovery_module_that_imports_a_translation_repository() -> None:
    path = APP_ROOT / "features" / "discovery" / "_synthetic.py"
    source = "from app.features.translation.snapshot_repository import SnapshotRepository\n"

    assert _translation_repository_hits(path, source=source) == [
        (1, "app.features.translation.snapshot_repository.SnapshotRepository")
    ]


def test_the_snapshot_enqueue_never_imports_a_discovery_repository() -> None:
    path = APP_ROOT / "features" / "translation" / "snapshot_enqueue.py"

    assert _discovery_repository_hits(path) == []


def test_with_no_target_locales_nothing_is_enqueued(db_session: Session) -> None:
    page = _catalogue(db_session, external_id="svc-no-locales")
    add_snapshot(db_session, page, SHA_A)

    SnapshotEnqueuer(db_session, ()).enqueue_pages([page.id])
    TranslationEnqueuer(db_session, ()).enqueue_many([], [page.id])

    assert db_session.scalar(select(func.count()).select_from(SnapshotTranslationTask)) == 0

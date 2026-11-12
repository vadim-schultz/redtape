"""The snapshot backfill counts pages, queues the missing and stale ones once, and resumes after --after (chapter 09)."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import NamedTuple
from uuid import UUID

from app.config import settings
from app.features.discovery.artifact_read import ArtifactReadService
from app.features.discovery.db_headroom import DatabaseSoftLimitError
from app.features.discovery.page_reads import ProcedurePageReads
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import (
    CatalogueService,
    DiscoveryCandidateMention,
    DiscoveryDocumentCandidate,
    DiscoveryMentionRole,
)
from app.models.snapshot_translation import SnapshotTranslationTask
from scripts.backfill_common import StopReason
from scripts.backfill_snapshot_translations import (
    BackfillMode,
    BackfillOptions,
    BackfillReport,
    _parse_options,
    format_report,
    run_backfill,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from embedding_support import NOW
from snapshot_machine_support import SHA_A, SHA_OLD, add_snapshot, stored_row
from test_discovery_admin_api import _catalogue


class OpenHeadroom:
    """Room for every write."""

    def ensure_room(self) -> None:
        """Never raise."""


class FullAfter:
    """Has room for ``batches`` checks, then reports the database at its limit."""

    def __init__(self, batches: int) -> None:
        self.left = batches

    def ensure_room(self) -> None:
        """Raise once the allowed batches are used up."""
        if self.left <= 0:
            raise DatabaseSoftLimitError("database_soft_limit")
        self.left -= 1


class Corpus(NamedTuple):
    """Procedure pages in each state the backfill tells apart, plus the snapshot-bearing ids in id order."""

    missing: CatalogueService
    stale: CatalogueService
    current: CatalogueService
    idle: CatalogueService
    unsnapshotted: CatalogueService
    ordered: list[UUID]


def _mention_on(session: Session, catalogue: CatalogueService, score: float) -> None:
    candidate = DiscoveryDocumentCandidate(
        jurisdiction_id=catalogue.jurisdiction_id, key=uuid.uuid4().hex, title_i18n={"de": "Antrag"}
    )
    session.add(candidate)
    session.flush()
    session.add(
        DiscoveryCandidateMention(
            candidate_id=candidate.id,
            catalogue_service_id=catalogue.id,
            role=DiscoveryMentionRole.REQUIRED,
            excerpt="Bitte bringen Sie den Ausweis mit.",
            source_field=f"details[{uuid.uuid4().hex[:6]}]",
            extractor="test",
            extractor_version="1",
            direct_category_confidence=score,
            category_codes=["home-and-housing"],
        )
    )
    session.flush()


def _page(session: Session, external_id: str, *, score: float | None = None, snapshot: bool = True) -> CatalogueService:
    catalogue = _catalogue(session, external_id=external_id)
    if snapshot:
        add_snapshot(session, catalogue, SHA_A)
    if score is not None:
        _mention_on(session, catalogue, score)
    return catalogue


def _corpus(session: Session) -> Corpus:
    missing = _page(session, "svc-missing", score=0.8)
    stale = _page(session, "svc-stale", score=0.6)
    stored_row(session, stale, "en", artifact_sha=SHA_OLD)
    current = _page(session, "svc-current", score=0.5)
    stored_row(session, current, "en", artifact_sha=SHA_A)
    idle = _page(session, "svc-idle")
    unsnapshotted = _page(session, "svc-unsnapshotted", score=0.7, snapshot=False)
    ordered = sorted(page.id for page in (missing, stale, current, idle))
    return Corpus(missing, stale, current, idle, unsnapshotted, ordered)


def _run(
    session: Session,
    headroom: OpenHeadroom | FullAfter | None = None,
    *,
    mode: BackfillMode = BackfillMode.WRITE,
    after: UUID | None = None,
    batch_size: int = 200,
    locale: str | None = "en",
    announce: list[str] | None = None,
) -> BackfillReport:
    options = BackfillOptions(after=after, batch_size=batch_size, locale=locale, mode=mode)
    lines = announce if announce is not None else []
    return run_backfill(session, options, headroom or OpenHeadroom(), announce=lines.append)


def _tasks(session: Session) -> list[SnapshotTranslationTask]:
    return list(session.scalars(select(SnapshotTranslationTask)))


def _task_count(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(SnapshotTranslationTask)) or 0)


def test_a_dry_run_counts_missing_stale_and_current_pages_and_writes_nothing(db_session: Session) -> None:
    _corpus(db_session)

    report = _run(db_session, mode=BackfillMode.DRY_RUN)

    assert (report.processed, report.totals.missing, report.totals.stale, report.totals.up_to_date) == (4, 1, 1, 1)
    assert report.totals.enqueued == 0
    assert _task_count(db_session) == 0


def test_a_write_run_queues_the_missing_and_stale_pages_with_the_counts_it_announces(db_session: Session) -> None:
    corpus = _corpus(db_session)
    announced: list[str] = []

    report = _run(db_session, announce=announced)

    assert (report.totals.enqueued, report.totals.missing, report.totals.stale) == (2, 1, 1)
    assert {task.catalogue_service_id for task in _tasks(db_session)} == {corpus.missing.id, corpus.stale.id}
    assert any("missing=1 stale=1 current=1" in line for line in announced)


def test_a_dry_run_reports_the_counts_a_write_run_then_acts_on(db_session: Session) -> None:
    _corpus(db_session)
    planned = _run(db_session, mode=BackfillMode.DRY_RUN)

    written = _run(db_session)

    assert (planned.totals.missing, planned.totals.stale) == (written.totals.missing, written.totals.stale)


def test_a_second_run_resumes_after_the_given_page_and_enqueues_nothing_new(db_session: Session) -> None:
    corpus = _corpus(db_session)
    _run(db_session)

    resumed = _run(db_session, after=corpus.ordered[1], batch_size=1)

    assert resumed.processed == len(corpus.ordered) - 2
    assert resumed.totals.enqueued == 0
    assert _task_count(db_session) == 2


def test_a_second_full_run_enqueues_nothing_new(db_session: Session) -> None:
    _corpus(db_session)
    _run(db_session)
    count_after_first = _task_count(db_session)

    second = _run(db_session)

    assert second.totals.enqueued == 0
    assert _task_count(db_session) == count_after_first


def test_a_page_with_a_candidate_queues_every_target_locale_when_no_locale_is_given(db_session: Session) -> None:
    page = _page(db_session, "svc-all-locales", score=0.8)

    _run(db_session, locale=None)

    locales = {task.locale for task in _tasks(db_session) if task.catalogue_service_id == page.id}
    assert locales == set(settings.translation_target_locale_codes)


def test_the_backfill_stops_at_the_database_soft_limit_and_names_where_to_resume(db_session: Session) -> None:
    for number in range(3):
        _page(db_session, f"svc-limit-{number}", score=0.5)

    report = _run(db_session, FullAfter(1), batch_size=1)

    assert (report.processed, report.stopped) == (1, StopReason.DB_LIMIT)
    assert f"--after {report.last_id}" in format_report(report)


def test_the_backfill_classifies_each_page_by_the_snapshot_the_worker_serves(db_session: Session) -> None:
    catalogue = _catalogue(db_session, external_id="svc-two-snapshots")
    add_snapshot(db_session, catalogue, SHA_OLD, fetched_at=NOW - timedelta(days=2))
    add_snapshot(db_session, catalogue, SHA_A, fetched_at=NOW - timedelta(days=1))

    served = ArtifactReadService(DiscoveryRepository(db_session), None, max_bytes=0).latest_snapshot(catalogue.id)
    read = ProcedurePageReads.for_session(db_session).latest_snapshots([catalogue.id])

    assert served is not None
    assert read[catalogue.id].sha256 == served.sha256 == SHA_A


def test_the_options_parse_the_dry_run_switch_and_the_resume_point() -> None:
    options = _parse_options(
        ["--after", "11111111-2222-3333-4444-555555555555", "--locale", "tr", "--batch-size", "5", "--dry-run"]
    )

    assert (options.locale, options.batch_size, options.mode) == ("tr", 5, BackfillMode.DRY_RUN)
    assert str(options.after) == "11111111-2222-3333-4444-555555555555"


def test_the_dry_run_switch_defaults_to_a_write_run() -> None:
    assert _parse_options([]).mode is BackfillMode.WRITE

"""Response models of the translation admin coverage route."""

from __future__ import annotations

from pydantic import BaseModel


class SnapshotLocaleCoverage(BaseModel):
    """Snapshot translation counts of one target locale, per procedure page.

    ``stale`` is a subset of ``translated``: a stored page that an open task is replacing.
    ``pending`` counts the ready pending tasks, as the card counts do.
    There is no ``unchanged`` count: an unchanged outcome keeps the stored page and completes its task,
    so the page leaves ``stale`` and ``pending``.
    """

    translated: int
    skipped: int
    stale: int
    pending: int
    failed: int


class TranslationLocaleCoverage(BaseModel):
    """Card and snapshot translation counts of one target locale.

    ``stale`` is a subset of ``translated``: a stored translation that an open task is replacing.
    ``pending`` counts the ready pending tasks, as the machine summary does.
    """

    locale: str
    translated: int
    stale: int
    pending: int
    claimed: int
    failed: int
    snapshot: SnapshotLocaleCoverage


class TranslationCoverageResponse(BaseModel):
    """Per target locale, how far the card units and the snapshot pages are translated.

    ``denominator`` counts the candidates with a German card; ``snapshot_denominator`` counts the procedure pages with
    an HTML snapshot, the pages a snapshot translation can be made from.
    """

    denominator: int
    snapshot_denominator: int
    locales: list[TranslationLocaleCoverage]

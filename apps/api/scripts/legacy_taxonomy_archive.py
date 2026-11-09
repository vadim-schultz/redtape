"""Archive the retired legacy taxonomy and prove each copy equals its source before the forward-only drop.

The archive schema is the only recovery source for retired rows (D-R1), so its integrity evidence must outlive the
source tables. Every archive copy is created once with ``CREATE TABLE IF NOT EXISTS ... AS SELECT`` and never
overwritten by a replay. Each copy is then compared with its source by row count and content checksum.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import Connection, Row, text

from scripts.category_mention_projection import project_axes

ARCHIVE_SCHEMA = "legacy_taxonomy_archive"
EVIDENCE_TABLE = "retirement_evidence"
RETIRED_TABLES: tuple[str, ...] = (
    "domain",
    "life_situation_group",
    "life_situation",
    "document_domain",
    "document_life_situation",
)
MENTION_TABLE = "discovery_candidate_mention"
MENTION_AXES_TABLE = "discovery_candidate_mention_axes"
MENTION_AXES_SELECT = f"""
    SELECT id, candidate_id, catalogue_service_id, domain_codes, situation_codes,
           direct_domain_confidence, direct_situation_confidence, pvog_leaf_code
    FROM {MENTION_TABLE}
"""
LOCKED_RELATIONS: tuple[str, ...] = (*RETIRED_TABLES, MENTION_TABLE)
MENTION_AXIS_ROWS_SQL = f"""
    SELECT domain_codes, situation_codes, direct_domain_confidence, direct_situation_confidence
    FROM {MENTION_TABLE}
"""
FINGERPRINT_SQL = """
    SELECT count(*), coalesce(md5(string_agg(r::text, chr(31) ORDER BY r::text)), '')
    FROM ({select}) AS r
"""
EVIDENCE_DDL = f"""
    CREATE TABLE IF NOT EXISTS {ARCHIVE_SCHEMA}.{EVIDENCE_TABLE} (
        table_name text PRIMARY KEY,
        row_count bigint NOT NULL,
        archive_checksum text NOT NULL,
        archived_at timestamptz NOT NULL DEFAULT now()
    )
"""


@dataclass(frozen=True, slots=True)
class Fingerprint:
    """Row count and order-independent content checksum of one relation."""

    row_count: int
    checksum: str


@dataclass(frozen=True, slots=True)
class ArchivedSource:
    """One retired relation: its archive table name and the SELECT that yields its rows."""

    name: str
    select_sql: str

    @property
    def archive_select(self) -> str:
        """Return the SELECT that yields the archived copy of this relation."""
        return f"SELECT * FROM {ARCHIVE_SCHEMA}.{self.name}"


ARCHIVED_SOURCES: tuple[ArchivedSource, ...] = (
    *(ArchivedSource(table, f"SELECT * FROM {table}") for table in RETIRED_TABLES),
    ArchivedSource(MENTION_AXES_TABLE, MENTION_AXES_SELECT),
)


@dataclass(frozen=True, slots=True)
class ArchiveCheck:
    """Source and archive fingerprints of one retired relation."""

    name: str
    source: Fingerprint
    archive: Fingerprint

    @property
    def matches(self) -> bool:
        """Return whether the archive copy equals its source by row count and checksum."""
        return self.source == self.archive

    def describe(self) -> str:
        """Return a one-line summary of the comparison for the operator."""
        verdict = "checksum matches" if self.source.checksum == self.archive.checksum else "checksum differs"
        return f"{self.name}: rows {self.source.row_count} vs {self.archive.row_count}, {verdict}"


class ArchiveMismatchError(RuntimeError):
    """Raised when at least one archive copy differs from its source; the migration transaction rolls back."""

    def __init__(self, checks: Sequence[ArchiveCheck]) -> None:
        """Name every mismatched relation in the message."""
        super().__init__("archive does not match source: " + "; ".join(check.describe() for check in checks))


@dataclass(frozen=True, slots=True)
class MentionAxisProfile:
    """How many mentions carry each legacy axis, and which legacy codes the projection cannot map."""

    mentions: int
    with_domain_codes: int
    with_situation_codes: int
    unknown_codes: list[str]


def mention_axis_profile(connection: Connection) -> MentionAxisProfile:
    """Count mentions per legacy axis and collect the codes the projection leaves unmapped."""
    rows = connection.execute(text(MENTION_AXIS_ROWS_SQL)).all()
    return MentionAxisProfile(
        mentions=len(rows),
        with_domain_codes=sum(row.domain_codes is not None for row in rows),
        with_situation_codes=sum(row.situation_codes is not None for row in rows),
        unknown_codes=_unknown_codes(rows),
    )


def _unknown_codes(rows: Iterable[Row]) -> list[str]:
    unknown: set[str] = set()
    for row in rows:
        projected = project_axes(
            domain_codes=row.domain_codes,
            situation_codes=row.situation_codes,
            direct_domain_confidence=row.direct_domain_confidence,
            direct_situation_confidence=row.direct_situation_confidence,
        )
        unknown.update(projected.unknown_values)
    return sorted(unknown)


def fingerprint(connection: Connection, select_sql: str) -> Fingerprint:
    """Return the row count and an order-independent md5 over the row text of ``select_sql``."""
    row_count, checksum = connection.execute(text(FINGERPRINT_SQL.format(select=select_sql))).one()
    return Fingerprint(row_count=int(row_count), checksum=str(checksum))


def archive_legacy_taxonomy(connection: Connection) -> None:
    """Lock the retired relations, then copy each into the archive once and record its archived count and checksum.

    The exclusive lock is taken first so that no writer can commit between the copy and the drop. A row written
    after the snapshot would otherwise be dropped without an archive copy.
    """
    connection.execute(text(f"LOCK TABLE {', '.join(LOCKED_RELATIONS)} IN ACCESS EXCLUSIVE MODE"))
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {ARCHIVE_SCHEMA}"))
    connection.execute(text(EVIDENCE_DDL))
    for source in ARCHIVED_SOURCES:
        _copy_once(connection, source)
        _record_evidence(connection, source.name, fingerprint(connection, source.archive_select))


def compare_archive(connection: Connection) -> tuple[ArchiveCheck, ...]:
    """Fingerprint every source and its archive copy, in the order of ``ARCHIVED_SOURCES``."""
    return tuple(
        ArchiveCheck(
            name=source.name,
            source=fingerprint(connection, source.select_sql),
            archive=fingerprint(connection, source.archive_select),
        )
        for source in ARCHIVED_SOURCES
    )


def _copy_once(connection: Connection, source: ArchivedSource) -> None:
    connection.execute(
        text(f"CREATE TABLE IF NOT EXISTS {ARCHIVE_SCHEMA}.{source.name} AS {source.select_sql}"),
    )


def _record_evidence(connection: Connection, name: str, archived: Fingerprint) -> None:
    """Record the archived count and checksum once; the first recorded values stay authoritative."""
    connection.execute(
        text(
            f"INSERT INTO {ARCHIVE_SCHEMA}.{EVIDENCE_TABLE} (table_name, row_count, archive_checksum) "
            "VALUES (:name, :count, :checksum) ON CONFLICT (table_name) DO NOTHING"
        ),
        {"name": name, "count": archived.row_count, "checksum": archived.checksum},
    )

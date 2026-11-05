"""Archive the retired legacy taxonomy rows, with row-count evidence, before the forward-only drop.

Every archive copy is created once with ``CREATE TABLE IF NOT EXISTS ... AS SELECT``. A later replay (a
downgrade followed by an upgrade) therefore never overwrites the first archive with empty recreated tables.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Connection, text

ARCHIVE_SCHEMA = "legacy_taxonomy_archive"
EVIDENCE_TABLE = "retirement_evidence"
ARCHIVED_TABLES: tuple[str, ...] = (
    "domain",
    "life_situation_group",
    "life_situation",
    "document_domain",
    "document_life_situation",
)
MENTION_AXES_TABLE = "discovery_candidate_mention_axes"
MENTION_AXES_SELECT = """
    SELECT id, candidate_id, catalogue_service_id, domain_codes, situation_codes,
           direct_domain_confidence, direct_situation_confidence, pvog_leaf_code
    FROM discovery_candidate_mention
"""


@dataclass(frozen=True, slots=True)
class ArchiveEvidence:
    """Rows preserved in the archive for one retired table."""

    table_name: str
    row_count: int


def archive_legacy_taxonomy(connection: Connection) -> tuple[ArchiveEvidence, ...]:
    """Copy each retired table into the archive schema once and return the archived row counts."""
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {ARCHIVE_SCHEMA}"))
    connection.execute(text(_evidence_ddl()))
    for table in ARCHIVED_TABLES:
        _copy_once(connection, table, f"SELECT * FROM {table}")
    _copy_once(connection, MENTION_AXES_TABLE, MENTION_AXES_SELECT)
    return _record_evidence(connection, (*ARCHIVED_TABLES, MENTION_AXES_TABLE))


def _evidence_ddl() -> str:
    return f"""
        CREATE TABLE IF NOT EXISTS {ARCHIVE_SCHEMA}.{EVIDENCE_TABLE} (
            table_name text PRIMARY KEY,
            row_count bigint NOT NULL,
            archived_at timestamptz NOT NULL DEFAULT now()
        )
    """


def _copy_once(connection: Connection, name: str, select_sql: str) -> None:
    connection.execute(text(f"CREATE TABLE IF NOT EXISTS {ARCHIVE_SCHEMA}.{name} AS {select_sql}"))


def _record_evidence(connection: Connection, names: Sequence[str]) -> tuple[ArchiveEvidence, ...]:
    """Record each archived count once; the first recorded count stays authoritative."""
    evidence: list[ArchiveEvidence] = []
    for name in names:
        count = connection.execute(text(f"SELECT count(*) FROM {ARCHIVE_SCHEMA}.{name}")).scalar_one()
        connection.execute(
            text(
                f"INSERT INTO {ARCHIVE_SCHEMA}.{EVIDENCE_TABLE} (table_name, row_count) "
                "VALUES (:name, :count) ON CONFLICT (table_name) DO NOTHING"
            ),
            {"name": name, "count": count},
        )
        evidence.append(ArchiveEvidence(name, int(count)))
    return tuple(evidence)

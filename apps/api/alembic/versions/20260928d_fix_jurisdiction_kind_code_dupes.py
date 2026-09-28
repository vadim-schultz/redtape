"""Fix jurisdiction (kind, code) uniqueness.

A prior migration (20260610_fix_dup_juris) deduped rows sharing the same
(geographic_parent_id, code), but a real (kind, code) pair must be globally
unique for a jurisdiction (country code, 2-digit Land code, 5-digit
Kreisschluessel, 8-digit AGS are all distinct across Germany). Leaked test
fixture rows had their own fake parent chain, so they shared (kind, code)
with the real imported row without sharing a parent -- undetected by that
migration. This dedupes on (kind, code) and adds the constraint that would
have prevented the leak outright.

Revision ID: 20260928d_fix_juris_kind_code
Revises: 20260928c_pending_edge_unique
Create Date: 2026-09-28
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260928d_fix_juris_kind_code"
down_revision: Union[str, None] = "20260928c_pending_edge_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean up rows that share (kind, code) before adding the constraint.
    # Strategy: Map all duplicates to keepers, update all FK references, then delete duplicates.
    # Mirrors 20260610_fix_dup_juris, but partitions by (kind, code) instead of
    # (geographic_parent_id, code).

    op.execute("""
        CREATE TEMP TABLE kind_code_duplicate_mapping AS
        WITH ranked AS (
            SELECT
                id,
                FIRST_VALUE(id) OVER (
                    PARTITION BY kind, code
                    ORDER BY last_updated ASC, id
                ) AS keeper_id,
                ROW_NUMBER() OVER (
                    PARTITION BY kind, code
                    ORDER BY last_updated ASC, id
                ) AS rn
            FROM jurisdiction
            WHERE code IS NOT NULL
        )
        SELECT id AS duplicate_id, keeper_id
        FROM ranked
        WHERE rn > 1
    """)

    # Repoint FKs from losers straight to the keeper.
    op.execute("""
        UPDATE locality
        SET municipality_id = dm.keeper_id
        FROM kind_code_duplicate_mapping dm
        WHERE locality.municipality_id = dm.duplicate_id
    """)
    op.execute("""
        UPDATE document
        SET jurisdiction_id = dm.keeper_id
        FROM kind_code_duplicate_mapping dm
        WHERE document.jurisdiction_id = dm.duplicate_id
    """)
    op.execute("""
        UPDATE document_requirement
        SET jurisdiction_id = dm.keeper_id
        FROM kind_code_duplicate_mapping dm
        WHERE document_requirement.jurisdiction_id = dm.duplicate_id
    """)

    # A loser's descendants (e.g. a leaked district and its leaked municipality)
    # have no counterpart in the keeper's real tree worth merging -- delete the
    # whole subtree rather than reparenting it.
    op.execute("""
        CREATE TEMP TABLE kind_code_duplicate_descendants AS
        WITH RECURSIVE descendants AS (
            SELECT duplicate_id AS id FROM kind_code_duplicate_mapping
            UNION
            SELECT j.id
            FROM jurisdiction j
            JOIN descendants d ON j.geographic_parent_id = d.id
        )
        SELECT id FROM descendants
    """)

    op.execute("""
        DELETE FROM locality
        WHERE municipality_id IN (SELECT id FROM kind_code_duplicate_descendants)
    """)
    op.execute("""
        DELETE FROM document_requirement
        WHERE jurisdiction_id IN (SELECT id FROM kind_code_duplicate_descendants)
    """)
    op.execute("""
        DELETE FROM document
        WHERE jurisdiction_id IN (SELECT id FROM kind_code_duplicate_descendants)
    """)
    op.execute("""
        DELETE FROM jurisdiction
        WHERE id IN (SELECT id FROM kind_code_duplicate_descendants)
    """)

    op.execute("DROP TABLE kind_code_duplicate_descendants")
    op.execute("DROP TABLE kind_code_duplicate_mapping")

    # Add the unique index (if it doesn't already exist). Partial: `code` is nullable.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'uq_jurisdiction_kind_code'
            ) THEN
                CREATE UNIQUE INDEX uq_jurisdiction_kind_code
                ON jurisdiction (kind, code)
                WHERE code IS NOT NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_jurisdiction_kind_code")

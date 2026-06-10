"""Fix jurisdiction unique constraint.

Revision ID: 20260610_fix_jurisdiction_constraint
Revises: 20260520_openplz_locations
Create Date: 2026-06-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260610_fix_jurisdiction_constraint"
down_revision: Union[str, None] = "20260520_openplz_locations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean up duplicate jurisdictions before adding constraint.
    # Keep the most recently updated row for each (geographic_parent_id, code) pair.
    
    # Step 1: Identify duplicates and the keeper for each group.
    # Create a mapping of (duplicate_id -> keeper_id).
    op.execute("""
        CREATE TEMP TABLE duplicate_mapping AS
        WITH ranked AS (
            SELECT
                id,
                FIRST_VALUE(id) OVER (
                    PARTITION BY COALESCE(geographic_parent_id::text, 'NULL'), COALESCE(code, 'NULL')
                    ORDER BY last_updated DESC, id
                ) AS keeper_id,
                ROW_NUMBER() OVER (
                    PARTITION BY COALESCE(geographic_parent_id::text, 'NULL'), COALESCE(code, 'NULL')
                    ORDER BY last_updated DESC, id
                ) AS rn
            FROM jurisdiction
        )
        SELECT id AS duplicate_id, keeper_id
        FROM ranked
        WHERE rn > 1
    """)
    
    # Step 2: Update child jurisdictions to point to the keeper instead of the duplicate.
    op.execute("""
        UPDATE jurisdiction
        SET geographic_parent_id = dm.keeper_id
        FROM duplicate_mapping dm
        WHERE jurisdiction.geographic_parent_id = dm.duplicate_id
    """)
    
    # Step 3: Delete the duplicate rows (now safe since no FKs reference them).
    op.execute("""
        DELETE FROM jurisdiction
        WHERE id IN (SELECT duplicate_id FROM duplicate_mapping)
    """)
    
    # Clean up temp table.
    op.execute("DROP TABLE duplicate_mapping")

    # Add the missing unique constraint.
    op.create_unique_constraint(
        "uq_jurisdiction_parent_code",
        "jurisdiction",
        ["geographic_parent_id", "code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_jurisdiction_parent_code", "jurisdiction", type_="unique")

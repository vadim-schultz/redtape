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
    # This must handle nested duplicates recursively.
    
    # Iteratively deduplicate until no duplicates remain.
    # Each iteration handles one level of the hierarchy.
    op.execute("""
        DO $$
        DECLARE
            duplicate_count INT;
        BEGIN
            LOOP
                -- Find duplicates and their keepers
                CREATE TEMP TABLE IF NOT EXISTS duplicate_mapping AS
                WITH ranked AS (
                    SELECT
                        id,
                        geographic_parent_id,
                        code,
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
                SELECT id AS duplicate_id, keeper_id, geographic_parent_id, code
                FROM ranked
                WHERE rn > 1;
                
                GET DIAGNOSTICS duplicate_count = ROW_COUNT;
                EXIT WHEN duplicate_count = 0;
                
                -- Update references in other tables that point to duplicates
                UPDATE locality
                SET municipality_id = dm.keeper_id
                FROM duplicate_mapping dm
                WHERE locality.municipality_id = dm.duplicate_id;
                
                UPDATE document
                SET jurisdiction_id = dm.keeper_id
                FROM duplicate_mapping dm
                WHERE document.jurisdiction_id = dm.duplicate_id;
                
                UPDATE document_requirement
                SET jurisdiction_id = dm.keeper_id
                FROM duplicate_mapping dm
                WHERE document_requirement.jurisdiction_id = dm.duplicate_id;
                
                -- Update children to point to keeper, skipping those that would create duplicates
                UPDATE jurisdiction j
                SET geographic_parent_id = dm.keeper_id
                FROM duplicate_mapping dm
                WHERE j.geographic_parent_id = dm.duplicate_id
                  AND NOT EXISTS (
                      -- Skip if this update would create a duplicate
                      SELECT 1 FROM jurisdiction j2
                      WHERE j2.geographic_parent_id = dm.keeper_id
                        AND j2.code = j.code
                        AND j2.id != j.id
                  );
                
                -- Delete children that would have created duplicates (they're duplicates themselves)
                DELETE FROM jurisdiction j
                WHERE EXISTS (
                    SELECT 1 FROM duplicate_mapping dm
                    WHERE j.geographic_parent_id = dm.duplicate_id
                      AND EXISTS (
                          SELECT 1 FROM jurisdiction j2
                          WHERE j2.geographic_parent_id = dm.keeper_id
                            AND j2.code = j.code
                            AND j2.id != j.id
                      )
                );
                
                -- Delete the duplicate parent rows (now safe)
                DELETE FROM jurisdiction
                WHERE id IN (SELECT duplicate_id FROM duplicate_mapping);
                
                -- Clean up for next iteration
                DROP TABLE duplicate_mapping;
            END LOOP;
        END $$;
    """)

    # Add the missing unique constraint.
    op.create_unique_constraint(
        "uq_jurisdiction_parent_code",
        "jurisdiction",
        ["geographic_parent_id", "code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_jurisdiction_parent_code", "jurisdiction", type_="unique")

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
    # Strategy: Map all duplicates to keepers, update all FK references, then delete duplicates.
    
    # Step 1: Identify all duplicates and their keepers
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
    
    # Step 2: Update all FK references in other tables to point to keepers
    op.execute("""
        UPDATE locality
        SET municipality_id = dm.keeper_id
        FROM duplicate_mapping dm
        WHERE locality.municipality_id = dm.duplicate_id
    """)
    
    op.execute("""
        UPDATE document
        SET jurisdiction_id = dm.keeper_id
        FROM duplicate_mapping dm
        WHERE document.jurisdiction_id = dm.duplicate_id
    """)
    
    op.execute("""
        UPDATE document_requirement
        SET jurisdiction_id = dm.keeper_id
        FROM duplicate_mapping dm
        WHERE document_requirement.jurisdiction_id = dm.duplicate_id
    """)
    
    # Step 3: Update self-referential FK (children pointing to duplicate parents)
    # Point all children to the keeper parent
    op.execute("""
        UPDATE jurisdiction
        SET geographic_parent_id = dm.keeper_id
        FROM duplicate_mapping dm
        WHERE jurisdiction.geographic_parent_id = dm.duplicate_id
    """)
    
    # Step 4: Now delete the duplicates (safe because nothing references them anymore)
    op.execute("""
        DELETE FROM jurisdiction
        WHERE id IN (SELECT duplicate_id FROM duplicate_mapping)
    """)
    
    # Step 5: Handle secondary duplicates created by reparenting
    # After moving children to keeper parents, some children might now be duplicates themselves
    # Repeat the process until no duplicates remain
    op.execute("""
        DO $$
        DECLARE
            dup_count INT;
        BEGIN
            LOOP
                -- Find new duplicates
                DROP TABLE IF EXISTS duplicate_mapping;
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
                WHERE rn > 1;
                
                GET DIAGNOSTICS dup_count = ROW_COUNT;
                EXIT WHEN dup_count = 0;
                
                -- Update references
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
                
                UPDATE jurisdiction
                SET geographic_parent_id = dm.keeper_id
                FROM duplicate_mapping dm
                WHERE jurisdiction.geographic_parent_id = dm.duplicate_id;
                
                -- Delete duplicates
                DELETE FROM jurisdiction
                WHERE id IN (SELECT duplicate_id FROM duplicate_mapping);
            END LOOP;
        END $$;
    """)
    
    # Clean up
    op.execute("DROP TABLE IF EXISTS duplicate_mapping")

    # Add the missing unique constraint.
    op.create_unique_constraint(
        "uq_jurisdiction_parent_code",
        "jurisdiction",
        ["geographic_parent_id", "code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_jurisdiction_parent_code", "jurisdiction", type_="unique")

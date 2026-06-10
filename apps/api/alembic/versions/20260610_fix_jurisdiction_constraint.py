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
    
    # Step 3: Identify children that would collide when reparented and map them to their keepers
    op.execute("""
        CREATE TEMP TABLE colliding_child_mapping AS
        SELECT 
            j.id AS colliding_id,
            j2.id AS keeper_id
        FROM jurisdiction j
        JOIN duplicate_mapping dm ON j.geographic_parent_id = dm.duplicate_id
        JOIN jurisdiction j2 ON j2.geographic_parent_id = dm.keeper_id AND j2.code = j.code
        WHERE j2.id != j.id
    """)
    
    # Step 3a: Find all descendants of colliding children (including the colliding children themselves)
    op.execute("""
        CREATE TEMP TABLE all_colliding_descendants AS
        WITH RECURSIVE descendants AS (
            SELECT colliding_id AS id, keeper_id FROM colliding_child_mapping
            UNION
            SELECT j.id, d.keeper_id
            FROM jurisdiction j
            JOIN descendants d ON j.geographic_parent_id = d.id
        )
        SELECT id, keeper_id FROM descendants
    """)
    
    # Step 3b: Update ALL FK references to colliding descendants to point to keepers
    op.execute("""
        UPDATE locality
        SET municipality_id = acd.keeper_id
        FROM all_colliding_descendants acd
        WHERE locality.municipality_id = acd.id
    """)
    
    op.execute("""
        UPDATE document
        SET jurisdiction_id = acd.keeper_id
        FROM all_colliding_descendants acd
        WHERE document.jurisdiction_id = acd.id
    """)
    
    op.execute("""
        UPDATE document_requirement
        SET jurisdiction_id = acd.keeper_id
        FROM all_colliding_descendants acd
        WHERE document_requirement.jurisdiction_id = acd.id
    """)
    
    # Step 3c: Now delete colliding children and their descendants (safe, nothing references them)
    op.execute("""
        DELETE FROM jurisdiction
        WHERE id IN (SELECT id FROM all_colliding_descendants)
    """)
    
    # Clean up temp tables
    op.execute("DROP TABLE all_colliding_descendants")
    
    # Clean up temp table
    op.execute("DROP TABLE colliding_child_mapping")
    
    # Step 4: Update self-referential FK (children pointing to duplicate parents)
    # Point remaining children to the keeper parent (safe now, no collisions)
    op.execute("""
        UPDATE jurisdiction
        SET geographic_parent_id = dm.keeper_id
        FROM duplicate_mapping dm
        WHERE jurisdiction.geographic_parent_id = dm.duplicate_id
    """)
    
    # Step 5: Now delete the duplicates (safe because nothing references them anymore)
    op.execute("""
        DELETE FROM jurisdiction
        WHERE id IN (SELECT duplicate_id FROM duplicate_mapping)
    """)
    
    # Step 6: Handle secondary duplicates created by reparenting
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

    # Add the unique constraint (if it doesn't already exist).
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'uq_jurisdiction_parent_code'
            ) THEN
                ALTER TABLE jurisdiction 
                ADD CONSTRAINT uq_jurisdiction_parent_code 
                UNIQUE (geographic_parent_id, code);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_constraint("uq_jurisdiction_parent_code", "jurisdiction", type_="unique")

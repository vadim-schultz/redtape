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
    op.execute("""
        DELETE FROM jurisdiction
        WHERE id IN (
            SELECT id
            FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY COALESCE(geographic_parent_id::text, 'NULL'), COALESCE(code, 'NULL')
                        ORDER BY last_updated DESC, id
                    ) AS rn
                FROM jurisdiction
            ) sub
            WHERE rn > 1
        )
    """)

    # Add the missing unique constraint.
    op.create_unique_constraint(
        "uq_jurisdiction_parent_code",
        "jurisdiction",
        ["geographic_parent_id", "code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_jurisdiction_parent_code", "jurisdiction", type_="unique")

"""Drop the superseded jurisdiction (geographic_parent_id, code) constraint.

`uq_jurisdiction_kind_code` (20260928d_fix_juris_kind_code) is the real
uniqueness guarantee for a jurisdiction: a (kind, code) pair is globally
unique for real German administrative codes regardless of parent. Keeping
the older `uq_jurisdiction_parent_code` constraint alongside it is now
redundant, and actively wrong once the importer intentionally reparents a
row onto its authoritative parent (see import_openplz_locations.py's
upsert_jurisdiction) -- a legitimate reparent could otherwise collide with
an unrelated row sharing the new (parent, code) pair.

Revision ID: 20260928e_drop_parent_code_uq
Revises: 20260928d_fix_juris_kind_code
Create Date: 2026-09-28
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260928e_drop_parent_code_uq"
down_revision: Union[str, None] = "20260928d_fix_juris_kind_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_jurisdiction_parent_code", "jurisdiction", type_="unique")


def downgrade() -> None:
    # Best-effort only: if duplicate (geographic_parent_id, code) rows were
    # introduced after this migration ran, this will fail -- not expected to
    # be run against production.
    op.create_unique_constraint(
        "uq_jurisdiction_parent_code",
        "jurisdiction",
        ["geographic_parent_id", "code"],
    )

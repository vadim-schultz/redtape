"""Add pvog_leaf_code to discovery_candidate_mention and document_life_situation.

Revision ID: 20261102_pvog_leaf_code
Revises: 20261102_life_situation_group
Create Date: 2026-11-02

Threads the raw PVOG leaf code (already discovered, already stashed as ``_personal_matter_code``) one
hop further than today: onto the mention (``discovery_candidate_mention.pvog_leaf_code``), and from there
onto the published document's situation tag at promotion time (``document_life_situation.pvog_leaf_code``)
— an optional, non-empty-only "more specific" facet under a situation (situation-tag-hierarchy chapter 3).
Both columns are nullable and additive: every existing row stays ``NULL``, behaviourally a no-op until a
PVOG-sourced mention populates it.

Not added to ``document_domain``: the facet is situation-only (chapter 3's own "Out of scope").
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261102_pvog_leaf_code"
down_revision: str | None = "20261102_life_situation_group"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("discovery_candidate_mention", sa.Column("pvog_leaf_code", sa.String(length=64), nullable=True))
    op.add_column("document_life_situation", sa.Column("pvog_leaf_code", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("document_life_situation", "pvog_leaf_code")
    op.drop_column("discovery_candidate_mention", "pvog_leaf_code")

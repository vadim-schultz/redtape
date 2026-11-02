"""Remove the four seeded sample documents and their three requirement edges.

Revision ID: 20261102_remove_seeded_documents
Revises: 20261102_pvog_leaf_code
Create Date: 2026-11-02

The catalogue is real data from the database (document-browse-confidence D6): ``scripts/seed_documents.py``
no longer creates the MVP sample documents, so the rows it already wrote to existing databases go too.
Only the exact stable ids the seed used are touched (``22222222-…2201``–``2204`` for documents,
``33333333-…3301``–``3303`` for requirements); a promoted or user-created document is never matched, even
with the same slug. ``document_domain`` and ``document_life_situation`` rows go by ``ON DELETE CASCADE``.
Jurisdictions stay (``document.jurisdiction_id`` is ``RESTRICT``). Re-running is a no-op.

Irreversible: the downgrade does nothing (seeded sample data, removal approved in D6).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261102_remove_seeded_documents"
down_revision: str | None = "20261102_pvog_leaf_code"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEEDED_DOCUMENT_IDS = tuple(f"22222222-2222-2222-2222-2222222222{n:02d}" for n in (1, 2, 3, 4))
SEEDED_REQUIREMENT_IDS = tuple(f"33333333-3333-3333-3333-3333333333{n:02d}" for n in (1, 2, 3))

DELETE_REQUIREMENTS = sa.text(
    "DELETE FROM document_requirement "
    "WHERE id IN :requirement_ids OR parent_document_id IN :document_ids OR required_document_id IN :document_ids"
).bindparams(
    sa.bindparam("requirement_ids", expanding=True),
    sa.bindparam("document_ids", expanding=True),
)
DELETE_DOCUMENTS = sa.text("DELETE FROM document WHERE id IN :document_ids").bindparams(
    sa.bindparam("document_ids", expanding=True)
)


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        DELETE_REQUIREMENTS,
        {"requirement_ids": list(SEEDED_REQUIREMENT_IDS), "document_ids": list(SEEDED_DOCUMENT_IDS)},
    )
    bind.execute(DELETE_DOCUMENTS, {"document_ids": list(SEEDED_DOCUMENT_IDS)})


def downgrade() -> None:
    """Irreversible: seeded sample data, removal approved in D6."""

"""Store the normalised official URL on document for duplicate detection.

Revision ID: 20261104_document_normalized_url
Revises: 20261102_remove_seeded_documents
Create Date: 2026-11-04

Adds ``document.normalized_url`` (nullable, ``String(1000)``) and the non-unique index
``ix_document_jurisdiction_normalized_url`` on ``(jurisdiction_id, normalized_url)``, then backfills the
column from ``official_url`` in keyset-paginated batches. The backfill only touches rows whose column is still
``NULL`` and whose ``official_url`` is not ``NULL``, so re-running it is a no-op.

The normalisation is a frozen copy of ``app.url_normalization.normalize_url`` (migrations are snapshots, so
importing the application module would change history if its rules changed later). The copy must stay
byte-for-byte equivalent in behaviour at this revision; ``tests/test_document_normalized_url_migration.py``
compares it with the application function on a corpus.

Downgrade drops the index and the column. No data is lost: the column is derived from ``official_url``.
"""

from collections.abc import Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import sqlalchemy as sa
from alembic import op

revision: str = "20261104_document_normalized_url"
down_revision: str | None = "20261102_remove_seeded_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_document_jurisdiction_normalized_url"
BATCH_SIZE = 1000
_TRACKING_PREFIXES = ("utm_",)
_TRACKING_EXACT = {"fbclid", "gclid"}


def _strip_tracking(query: str) -> str:
    pairs = parse_qsl(query, keep_blank_values=True)
    kept = [(k, v) for k, v in pairs if not k.startswith(_TRACKING_PREFIXES) and k not in _TRACKING_EXACT]
    return urlencode(kept)


def _sort_query(query: str) -> str:
    return urlencode(sorted(parse_qsl(query, keep_blank_values=True)))


def _trim_path(path: str) -> str:
    return path[:-1] if path.endswith("/") and path != "/" else path


def _normalize_url(url: str) -> str:
    """Frozen copy of ``normalize_url`` at this revision."""
    parts = urlsplit(url)
    query = _sort_query(_strip_tracking(parts.query))
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), _trim_path(parts.path), query, ""))


def _backfill_normalized_url(connection: sa.Connection) -> None:
    """Fill ``normalized_url`` for rows that have an ``official_url`` and no stored value yet, in id order."""
    select_batch = sa.text(
        "SELECT id, official_url FROM document "
        "WHERE official_url IS NOT NULL AND normalized_url IS NULL AND id > CAST(:last_id AS uuid) "
        "ORDER BY id LIMIT :limit"
    )
    update_row = sa.text("UPDATE document SET normalized_url = :normalized WHERE id = :id")
    last_id: object = "00000000-0000-0000-0000-000000000000"
    while True:
        rows = connection.execute(select_batch, {"last_id": last_id, "limit": BATCH_SIZE}).all()
        if not rows:
            return
        for doc_id, official_url in rows:
            connection.execute(update_row, {"id": doc_id, "normalized": _normalize_url(official_url)})
        last_id = rows[-1][0]


def upgrade() -> None:
    op.add_column("document", sa.Column("normalized_url", sa.String(length=1000), nullable=True))
    op.create_index(INDEX_NAME, "document", ["jurisdiction_id", "normalized_url"], unique=False)
    _backfill_normalized_url(op.get_bind())


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="document")
    op.drop_column("document", "normalized_url")

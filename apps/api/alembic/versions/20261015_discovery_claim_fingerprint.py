"""Add discovery_claim.payload_fingerprint for idempotent append.

Revision ID: 20261015_claim_fingerprint
Revises: 20261012_discovery_staging
Create Date: 2026-10-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261015_claim_fingerprint"
down_revision: str | None = "20261012_discovery_staging"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "discovery_claim",
        sa.Column("payload_fingerprint", sa.String(length=64), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE discovery_claim SET payload_fingerprint = 'legacy-' || id::text "
            "WHERE payload_fingerprint IS NULL"
        )
    )
    op.alter_column("discovery_claim", "payload_fingerprint", nullable=False)
    op.create_unique_constraint(
        "uq_discovery_claim_entity_kind_fingerprint",
        "discovery_claim",
        ["discovery_entity_id", "kind", "payload_fingerprint"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_discovery_claim_entity_kind_fingerprint", "discovery_claim", type_="unique")
    op.drop_column("discovery_claim", "payload_fingerprint")

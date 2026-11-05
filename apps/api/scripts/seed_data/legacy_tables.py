"""Frozen column shapes of the retired legacy taxonomy tables.

Historical Alembic revisions and the one-time archive step read the legacy tables through these lightweight
definitions instead of the ORM models, which were removed in Chapter 9. Only the columns those steps touch
are declared; nothing in the running application imports this module.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

LEGACY_METADATA = sa.MetaData()


def _uuid_column(name: str) -> sa.Column:
    return sa.Column(name, sa.Uuid(as_uuid=True))


DOMAIN = sa.Table(
    "domain",
    LEGACY_METADATA,
    _uuid_column("id"),
    sa.Column("code", sa.String(length=64)),
)
LIFE_SITUATION_GROUP = sa.Table(
    "life_situation_group",
    LEGACY_METADATA,
    _uuid_column("id"),
    sa.Column("code", sa.String(length=64)),
)
LIFE_SITUATION = sa.Table(
    "life_situation",
    LEGACY_METADATA,
    _uuid_column("id"),
    sa.Column("code", sa.String(length=64)),
    _uuid_column("group_id"),
)
DOCUMENT_DOMAIN = sa.Table(
    "document_domain",
    LEGACY_METADATA,
    _uuid_column("document_id"),
    _uuid_column("domain_id"),
    sa.Column("confidence", sa.Float()),
)
DOCUMENT_LIFE_SITUATION = sa.Table(
    "document_life_situation",
    LEGACY_METADATA,
    _uuid_column("document_id"),
    _uuid_column("life_situation_id"),
    sa.Column("confidence", sa.Float()),
    sa.Column("pvog_leaf_code", sa.String(length=64)),
)
MENTION_LEGACY_COLUMNS = sa.Table(
    "discovery_candidate_mention",
    LEGACY_METADATA,
    _uuid_column("id"),
    sa.Column("domain_codes", postgresql.ARRAY(sa.String(length=64))),
    sa.Column("situation_codes", postgresql.ARRAY(sa.String(length=64))),
    sa.Column("direct_domain_confidence", sa.Float()),
    sa.Column("direct_situation_confidence", sa.Float()),
)

"""The order in which a mention role describes a candidate: required, then form, then issued (D4)."""

from __future__ import annotations

from sqlalchemy import Case, case

from app.models.discovery import DiscoveryCandidateMention as Mention
from app.models.discovery import DiscoveryMentionRole

ROLE_ORDER = (DiscoveryMentionRole.REQUIRED, DiscoveryMentionRole.FORM, DiscoveryMentionRole.ISSUED)


def role_rank(role: DiscoveryMentionRole) -> int:
    """Return the position of ``role`` in :data:`ROLE_ORDER`; lower describes the candidate better."""
    return ROLE_ORDER.index(role)


def role_rank_column() -> Case[int]:
    """Return the SQL expression of :func:`role_rank` over the mention role."""
    return case({role: rank for rank, role in enumerate(ROLE_ORDER)}, value=Mention.role)

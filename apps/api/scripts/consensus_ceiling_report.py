"""Report the consensus ceiling over production discovery candidates (chapter 2, situation-tag-coverage, LR2).

Run from `apps/api`:
  python -m scripts.consensus_ceiling_report
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from app.db import SessionLocal
from app.features.discovery.consensus_ceiling import consensus_ceiling
from app.models.discovery import DiscoveryCandidateMention, DiscoveryDocumentCandidate
from sqlalchemy.orm import Session


def _candidate_ids(session: Session) -> list[uuid.UUID]:
    return list(session.scalars(sa.select(DiscoveryDocumentCandidate.id)))


def _mentions(session: Session) -> list[tuple[uuid.UUID, uuid.UUID]]:
    return list(
        session.execute(
            sa.select(DiscoveryCandidateMention.candidate_id, DiscoveryCandidateMention.catalogue_service_id)
        )
    )


def main() -> None:
    """Print the consensus ceiling over the production discovery candidates."""
    with SessionLocal() as session:
        ceiling = consensus_ceiling(_candidate_ids(session), _mentions(session))
    print(
        f"consensus ceiling: {ceiling.total_candidates} candidates, "
        f"{ceiling.at_or_above_floor} ({ceiling.share_at_or_above_floor:.1%}) at or above the floor, "
        f"{ceiling.exactly_one} ({ceiling.share_exactly_one:.1%}) at exactly one procedure, "
        f"{ceiling.zero} ({ceiling.share_zero:.1%}) at zero"
    )


if __name__ == "__main__":
    main()

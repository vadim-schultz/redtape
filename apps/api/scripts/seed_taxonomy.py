"""Idempotent seed: Germany domains, life situation groups and life situations.

Run from `apps/api`:
  python -m scripts.seed_taxonomy
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from app.db import SessionLocal
from app.models.taxonomy import Domain, LifeSituation, LifeSituationGroup
from sqlalchemy.orm import Session

from scripts.seed_data.taxonomy import (
    DOMAINS,
    SITUATION_GROUP_CODES,
    SITUATION_GROUPS,
    SITUATIONS,
    Term,
    term_id,
)

TermModel = type[Domain] | type[LifeSituation] | type[LifeSituationGroup]


def _upsert_terms(session: Session, model: TermModel, terms: Iterable[Term]) -> None:
    for term in terms:
        session.merge(
            model(
                id=term.id,
                code=term.code,
                name_i18n=term.name_i18n,
                description_i18n=term.description_i18n,
                icon=term.icon,
                sort_order=term.sort_order,
            )
        )


def _assign_situation_groups(session: Session) -> None:
    for situation in session.scalars(sa.select(LifeSituation)):
        situation.group_id = term_id(SITUATION_GROUP_CODES[situation.code])


def seed_taxonomy(session: Session) -> None:
    _upsert_terms(session, LifeSituationGroup, SITUATION_GROUPS)
    _upsert_terms(session, Domain, DOMAINS)
    _upsert_terms(session, LifeSituation, SITUATIONS)
    session.flush()
    _assign_situation_groups(session)


def main() -> None:
    with SessionLocal() as session:
        seed_taxonomy(session)
        session.commit()
    print("seed_taxonomy: 13 domains, 8 situation groups and 18 life situations upserted.")


if __name__ == "__main__":
    main()

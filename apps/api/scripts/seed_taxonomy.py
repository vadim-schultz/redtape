"""Idempotent seed: Germany domains, life situations and tags on the seeded documents.

Run from `apps/api` (after `seed_documents`):
  python -m scripts.seed_taxonomy
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping

import sqlalchemy as sa
from app.db import SessionLocal
from app.models.taxonomy import Domain, LifeSituation, document_domain, document_life_situation
from sqlalchemy.orm import Session

from scripts.seed_data.taxonomy import DOCUMENT_TAGS, DOMAINS, SITUATIONS, Term, term_id

Tags = Mapping[uuid.UUID, tuple[tuple[str, ...], tuple[str, ...]]]


def _upsert_terms(session: Session, model: type[Domain] | type[LifeSituation], terms: Iterable[Term]) -> None:
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


def _link(session: Session, table: sa.Table, column: str, pairs: set[tuple[uuid.UUID, uuid.UUID]]) -> None:
    existing = {(row[0], row[1]) for row in session.execute(sa.select(table.c.document_id, table.c[column]))}
    rows = [{"document_id": doc, column: term} for doc, term in pairs - existing]
    if rows:
        session.execute(sa.insert(table), rows)


def _validate_tags(tags: Tags) -> None:
    known = {t.code for t in DOMAINS + SITUATIONS}
    unknown = {code for domains, situations in tags.values() for code in (*domains, *situations)} - known
    if unknown:
        raise ValueError(f"tag map references unknown codes: {sorted(unknown)}")


def _tag_documents(session: Session, tags: Tags) -> None:
    domain_pairs = {(doc, term_id(c)) for doc, (domains, _) in tags.items() for c in domains}
    situation_pairs = {(doc, term_id(c)) for doc, (_, situations) in tags.items() for c in situations}
    _link(session, document_domain, "domain_id", domain_pairs)
    _link(session, document_life_situation, "life_situation_id", situation_pairs)


def seed_taxonomy(session: Session, tags: Tags = DOCUMENT_TAGS) -> None:
    _validate_tags(tags)
    _upsert_terms(session, Domain, DOMAINS)
    _upsert_terms(session, LifeSituation, SITUATIONS)
    session.flush()
    _tag_documents(session, tags)


def main() -> None:
    with SessionLocal() as session:
        seed_taxonomy(session)
        session.commit()
    print("seed_taxonomy: 13 domains, 18 life situations and document tags upserted.")


if __name__ == "__main__":
    main()

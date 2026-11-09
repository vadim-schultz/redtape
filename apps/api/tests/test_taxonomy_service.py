from __future__ import annotations

import pytest
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyCodeError, TaxonomyService
from app.models.taxonomy import Category
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def service(db_session: Session) -> TaxonomyService:
    seed_canonical_taxonomy(db_session)
    db_session.flush()
    return TaxonomyService(TaxonomyRepository(db_session))


def _id_of(session: Session, code: str):
    return session.scalar(select(Category.id).where(Category.code == code))


def test_resolves_known_category_codes_to_ids(service: TaxonomyService, db_session: Session) -> None:
    codes = ["home-and-housing", "moving-house"]

    assert service.resolve_category_ids(codes) == [_id_of(db_session, code) for code in codes]


def test_known_category_codes_returns_only_the_canonical_ones(service: TaxonomyService) -> None:
    assert service.known_category_codes(["home-and-housing", "no-such-code"]) == {"home-and-housing"}


def test_expanding_a_parent_category_includes_its_children(service: TaxonomyService) -> None:
    assert service.expand_category_codes(["home-and-housing"]) == (
        "home-and-housing",
        "moving-house",
        "renting-home",
        "buying-property",
    )


def test_unknown_category_code_raises_naming_it(service: TaxonomyService) -> None:
    with pytest.raises(TaxonomyCodeError, match="no-such-code"):
        service.require_category_codes(["no-such-code"])


def test_expanding_an_unknown_category_code_raises(service: TaxonomyService) -> None:
    with pytest.raises(TaxonomyCodeError, match="no-such-code"):
        service.expand_category_codes(["no-such-code"])

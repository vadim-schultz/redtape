from __future__ import annotations

import pytest
from app.features.taxonomy.repository import TaxonomyRepository
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy.orm import Session


@pytest.fixture
def repo(db_session: Session) -> TaxonomyRepository:
    seed_canonical_taxonomy(db_session)
    db_session.flush()
    return TaxonomyRepository(db_session)


def test_list_categories_returns_roots_and_children_in_contract_order(repo: TaxonomyRepository) -> None:
    categories = repo.list_categories()

    assert [category.code for category in categories[:3]] == [
        "family-and-relationships",
        "birth-and-parenthood",
        "marriage-and-partnership",
    ]
    assert categories[1].parent_id == categories[0].id


def test_category_descendants_include_the_selected_root_and_not_siblings(repo: TaxonomyRepository) -> None:
    descendants = repo.category_descendant_codes(("home-and-housing",))

    assert descendants == ("home-and-housing", "moving-house", "renting-home", "buying-property")


def test_category_descendants_of_an_unknown_code_are_empty(repo: TaxonomyRepository) -> None:
    assert repo.category_descendant_codes(("no-such-category",)) == ()

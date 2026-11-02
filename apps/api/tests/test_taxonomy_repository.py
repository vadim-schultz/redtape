from __future__ import annotations

import pytest
from app.features.taxonomy.repository import TaxonomyRepository
from app.models.taxonomy import LifeSituationGroup
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy.orm import Session


@pytest.fixture
def repo(db_session: Session) -> TaxonomyRepository:
    # tags={}: this suite only needs the vocabulary, not the document tags, which
    # reference a document graph this fixture never seeds.
    seed_taxonomy(db_session)
    db_session.flush()
    return TaxonomyRepository(db_session)


def test_list_terms_returns_all_8_situation_groups_in_sort_order(repo: TaxonomyRepository) -> None:
    groups = repo.list_terms(LifeSituationGroup)

    assert len(groups) == 8
    assert [g.sort_order for g in groups] == sorted(g.sort_order for g in groups)


def test_list_situations_with_group_returns_the_right_group_code_per_situation(repo: TaxonomyRepository) -> None:
    rows = repo.list_situations_with_group()

    by_code = {situation.code: group_code for situation, group_code in rows}
    assert len(rows) == 18
    assert by_code["moving-house"] == "home-housing"
    assert by_code["retirement"] == "retirement"

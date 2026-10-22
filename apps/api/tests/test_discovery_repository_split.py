"""The discovery repositories are split by aggregate and only run queries."""

from __future__ import annotations

import uuid

import pytest
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.repository.activity import ActivityRepository
from app.features.discovery.repository.catalogue import CatalogueRepository
from app.features.discovery.repository.claims import ClaimRepository
from app.features.discovery.repository.coverage import CoverageRepository
from app.features.discovery.repository.entities import EntityRepository
from app.features.discovery.repository.task_listing import TaskListingRepository
from app.features.discovery.repository.tasks import TaskRepository
from app.models.discovery import DiscoveryClaimKind
from sqlalchemy.orm import Session

AGGREGATES = (
    ActivityRepository,
    CatalogueRepository,
    ClaimRepository,
    CoverageRepository,
    EntityRepository,
    TaskListingRepository,
    TaskRepository,
)
BUSINESS_METHODS = ("upsert_catalogue_item", "append_claim")


@pytest.mark.parametrize("repository_class", AGGREGATES)
def test_each_aggregate_repository_is_usable_on_its_own(db_session: Session, repository_class: type) -> None:
    repository = repository_class(db_session)
    assert isinstance(repository, repository_class)
    assert isinstance(DiscoveryRepository(db_session), repository_class)


@pytest.mark.parametrize("name", BUSINESS_METHODS)
def test_repositories_no_longer_hold_business_methods(name: str) -> None:
    assert not hasattr(DiscoveryRepository, name)


def test_claim_repository_finds_nothing_for_unknown_fingerprint(db_session: Session) -> None:
    found = ClaimRepository(db_session).find_claim_by_fingerprint(
        discovery_entity_id=uuid.uuid4(), kind=DiscoveryClaimKind.NEW_DOCUMENT, payload_fingerprint="nope"
    )
    assert found is None

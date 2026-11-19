"""The cleaned-text hash of a completed extraction: recorded on completion, and read back for the same page and versions."""

from __future__ import annotations

import uuid

import pytest
from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.models.discovery import CatalogueService, DiscoveryTask, DiscoveryTaskKind, DiscoveryTaskStatus
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue
from test_discovery_machine_api import _issue_key
from test_discovery_machine_api import client as machine_client  # noqa: F401

PAGE_URL = "https://example.gov/leistung/anmeldung"
INPUT_KEY = "llm:0a1b2c3d"
TEXT_HASH = "ab" * 32
OTHER_HASH = "cd" * 32
EXTRACTED_URL = "/api/v1/discovery/machine/tasks/text-extracted"
COMPLETE_URL = "/api/v1/discovery/machine/tasks/{task_id}/complete"


def _extraction(
    session: Session,
    catalogue: CatalogueService,
    *,
    status: DiscoveryTaskStatus = DiscoveryTaskStatus.COMPLETED,
    text_hash: str | None = TEXT_HASH,
) -> DiscoveryTask:
    """Return an ``llm_extract`` task for the page with ``text_hash`` recorded and the given status."""
    target = TaskTarget(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.LLM_EXTRACT,
        target_url=PAGE_URL,
        input_key=INPUT_KEY,
    )
    task = DiscoveryRepository(session).insert_task(target)
    task.status = status
    task.text_hash = text_hash
    session.flush()
    return task


def _extracted(http: TestClient[Litestar], key: str, catalogue_id: uuid.UUID, **overrides: str) -> bool:
    """Ask whether the page's extraction under ``INPUT_KEY`` completed with the text hash, with ``overrides`` changed."""
    query = {
        "catalogue_service_id": str(catalogue_id),
        "target_url": PAGE_URL,
        "input_key": INPUT_KEY,
        "text_hash": TEXT_HASH,
        **overrides,
    }
    response = http.get(EXTRACTED_URL, params=query, headers={"X-API-Key": key})
    assert response.status_code == 200
    return bool(response.json()["extracted"])


def test_a_completed_extraction_of_the_same_text_for_the_page_is_known(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """discovery text · happy: a completed extraction with this hash, page and input key is reported as extracted."""
    catalogue = _catalogue(db_session)
    _extraction(db_session, catalogue)
    key = _issue_key(db_session)

    assert _extracted(machine_client, key, catalogue.id) is True


@pytest.mark.parametrize(
    "change",
    [
        {"text_hash": OTHER_HASH},
        {"input_key": "llm:ffffffff"},
        {"target_url": "https://example.gov/other"},
    ],
)
def test_a_different_text_or_version_or_page_is_not_known(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    change: dict[str, str],
) -> None:
    """discovery text · negative: another hash, input key (model or prompt version) or page does not count as extracted."""
    catalogue = _catalogue(db_session)
    _extraction(db_session, catalogue)
    key = _issue_key(db_session)

    assert _extracted(machine_client, key, catalogue.id, **change) is False


def test_an_extraction_that_has_not_completed_is_not_known(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """discovery text · negative: a pending extraction is not yet an extraction, so the same text is not known."""
    catalogue = _catalogue(db_session)
    _extraction(db_session, catalogue, status=DiscoveryTaskStatus.PENDING)
    key = _issue_key(db_session)

    assert _extracted(machine_client, key, catalogue.id) is False


def test_completing_a_task_records_its_text_hash(machine_client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    """discovery text · happy: the completion keeps the hash of the text the model read."""
    catalogue = _catalogue(db_session)
    task = DiscoveryRepository(db_session).insert_task(
        TaskTarget(
            catalogue_service_id=catalogue.id,
            kind=DiscoveryTaskKind.LLM_EXTRACT,
            target_url=PAGE_URL,
            input_key=INPUT_KEY,
        )
    )
    key = _issue_key(db_session)

    response = machine_client.post(
        COMPLETE_URL.format(task_id=task.id),
        json={"note": "docs=2 edges=1 dropped=0", "text_hash": TEXT_HASH},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 201
    recorded = db_session.get(DiscoveryTask, task.id)
    assert recorded is not None and recorded.text_hash == TEXT_HASH


def test_a_text_hash_that_is_not_sha256_hex_is_rejected(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """discovery text · negative: a completion whose hash is not 64 lowercase hex characters is refused and changes nothing."""
    catalogue = _catalogue(db_session)
    task = DiscoveryRepository(db_session).insert_task(
        TaskTarget(
            catalogue_service_id=catalogue.id,
            kind=DiscoveryTaskKind.LLM_EXTRACT,
            target_url=PAGE_URL,
            input_key=INPUT_KEY,
        )
    )
    key = _issue_key(db_session)

    response = machine_client.post(
        COMPLETE_URL.format(task_id=task.id),
        json={"text_hash": "not-a-hash"},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 422
    recorded = db_session.get(DiscoveryTask, task.id)
    assert recorded is not None and recorded.text_hash is None

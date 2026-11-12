"""The mention hook queues one snapshot translation per target locale for each procedure page a mention cites (chapter 09)."""

from __future__ import annotations

import pytest
from app.config import settings
from app.features.translation.priority import snapshot_first_priority
from app.features.translation.source import SourceRepository
from app.models.discovery import CatalogueService, DiscoveryDocumentCandidate
from app.models.search import WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslationTask
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy import select
from sqlalchemy.orm import Session

from snapshot_machine_support import SHA_A, add_snapshot, stored_row
from test_discovery_admin_api import _catalogue
from test_discovery_candidates_api import _item, _post
from test_discovery_machine_api import _issue_key, client  # noqa: F401


@pytest.fixture
def vocabulary(db_session: Session) -> None:
    seed_canonical_taxonomy(db_session)


def _page(session: Session, external_id: str, *, with_snapshot: bool = True) -> CatalogueService:
    catalogue = _catalogue(session, external_id=external_id)
    if with_snapshot:
        add_snapshot(session, catalogue, SHA_A)
    return catalogue


def _mention(
    catalogue: CatalogueService, title: str, score: float, source_field: str = "details[0]"
) -> dict[str, object]:
    return _item(
        catalogue,
        title_i18n={"de": title},
        source_field=source_field,
        category_codes=["home-and-housing"],
        direct_category_confidence=score,
    )


def _tasks_of(session: Session, catalogue_id: object) -> list[SnapshotTranslationTask]:
    session.flush()
    stmt = (
        select(SnapshotTranslationTask)
        .where(SnapshotTranslationTask.catalogue_service_id == catalogue_id)
        .execution_options(populate_existing=True)
    )
    return list(session.scalars(stmt))


def _confidence_by_title(session: Session) -> dict[str, float]:
    candidates = list(session.scalars(select(DiscoveryDocumentCandidate)))
    scores = SourceRepository(session).confidences_for([candidate.id for candidate in candidates])
    return {candidate.title_i18n["de"]: scores[candidate.id] for candidate in candidates}


def test_a_recorded_mention_queues_one_snapshot_task_per_target_locale_at_the_best_confidence(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    key = _issue_key(db_session)
    page = _page(db_session, "svc-mention")

    response = _post(client, key, _mention(page, "Personalausweis", 0.9))

    assert response.status_code == 200
    tasks = _tasks_of(db_session, page.id)
    strong = _confidence_by_title(db_session)["Personalausweis"]
    assert {task.locale for task in tasks} == set(settings.translation_target_locale_codes)
    assert {(task.source_hash, task.status) for task in tasks} == {(SHA_A, WorkTaskStatus.PENDING)}
    assert {task.priority for task in tasks} == {snapshot_first_priority([strong])}


def test_a_second_candidate_on_the_same_page_adds_no_second_task(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    key = _issue_key(db_session)
    page = _page(db_session, "svc-two-candidates")

    response = _post(
        client,
        key,
        _mention(page, "Personalausweis", 0.9),
        _mention(page, "Geburtsurkunde", 0.3, source_field="details[1]"),
    )

    assert response.status_code == 200
    tasks = _tasks_of(db_session, page.id)
    strong = _confidence_by_title(db_session)["Personalausweis"]
    assert len(tasks) == len(settings.translation_target_locale_codes)
    assert {task.priority for task in tasks} == {snapshot_first_priority([strong])}


def test_a_weaker_candidate_recorded_later_does_not_lower_the_page_priority(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    key = _issue_key(db_session)
    page = _page(db_session, "svc-later-weaker")
    _post(client, key, _mention(page, "Personalausweis", 0.9))

    response = _post(client, key, _mention(page, "Geburtsurkunde", 0.3, source_field="details[1]"))

    assert response.status_code == 200
    strong = _confidence_by_title(db_session)["Personalausweis"]
    assert {task.priority for task in _tasks_of(db_session, page.id)} == {snapshot_first_priority([strong])}


def test_a_page_whose_translation_matches_the_latest_sha_enqueues_nothing(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    key = _issue_key(db_session)
    page = _page(db_session, "svc-current")
    for locale in settings.translation_target_locale_codes:
        stored_row(db_session, page, locale, artifact_sha=SHA_A)

    response = _post(client, key, _mention(page, "Personalausweis", 0.9))

    assert response.status_code == 200
    assert _tasks_of(db_session, page.id) == []


def test_a_page_without_a_snapshot_enqueues_nothing(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    key = _issue_key(db_session)
    page = _page(db_session, "svc-no-snapshot", with_snapshot=False)

    response = _post(client, key, _mention(page, "Personalausweis", 0.9))

    assert response.status_code == 200
    assert _tasks_of(db_session, page.id) == []

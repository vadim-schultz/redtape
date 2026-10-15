"""HTTP and mapping tests for discovery emit preview."""

from __future__ import annotations

import uuid

from app.features.discovery.emit_preview import build_emit_preview_items
from app.main import Litestar
from app.models.discovery import (
    DiscoveryClaim,
    DiscoveryClaimKind,
    DiscoveryEntity,
    DiscoverySource,
)
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue, _token

EMIT_PREVIEW_URL = "/api/v1/discovery/admin/catalogue/{catalogue_id}/emit-preview"


def test_emit_preview_maps_new_document_claim_to_suggestion_shaped_payload(
    db_session: Session,
) -> None:
    catalogue = _catalogue(db_session)
    entity = DiscoveryEntity(
        catalogue_service_id=catalogue.id,
        canonical_url="https://example.gov/doc",
        label="Doc",
    )
    db_session.add(entity)
    db_session.flush()
    claim = DiscoveryClaim(
        discovery_entity_id=entity.id,
        kind=DiscoveryClaimKind.NEW_DOCUMENT,
        payload={
            "title_i18n": {"de": "Ausweis"},
            "official_url": "https://example.gov/doc",
        },
        payload_fingerprint="preview-doc-fp",
    )
    db_session.add(claim)
    db_session.flush()

    items = build_emit_preview_items(
        claims=[claim],
        entities_by_id={entity.id: entity},
        jurisdiction_id=catalogue.jurisdiction_id,
    )

    assert len(items) == 1
    assert items[0]["skip_reason"] is None
    assert items[0]["payload"] is not None
    assert items[0]["payload"]["kind"] == "new_document"
    assert items[0]["payload"]["source_url"] == entity.canonical_url


def test_emit_preview_marks_unresolved_requirement_claim_with_skip_reason(
    db_session: Session,
) -> None:
    catalogue = _catalogue(db_session)
    entity = DiscoveryEntity(
        catalogue_service_id=catalogue.id,
        canonical_url="https://example.gov/req",
    )
    db_session.add(entity)
    db_session.flush()
    claim = DiscoveryClaim(
        discovery_entity_id=entity.id,
        kind=DiscoveryClaimKind.NEW_REQUIREMENT,
        payload={"notes_i18n": {"de": "Braucht Pass"}},
        payload_fingerprint="preview-req-fp",
    )
    db_session.add(claim)
    db_session.flush()

    items = build_emit_preview_items(
        claims=[claim],
        entities_by_id={entity.id: entity},
        jurisdiction_id=catalogue.jurisdiction_id,
    )

    assert items[0]["payload"] is None
    assert items[0]["skip_reason"] == "unresolved_requirement_documents"


def test_get_emit_preview_returns_403_for_non_admin(client: TestClient[Litestar], db_session: Session) -> None:
    catalogue = _catalogue(db_session, source=DiscoverySource.GOVDATA)

    response = client.get(
        EMIT_PREVIEW_URL.format(catalogue_id=catalogue.id),
        headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email='stranger@example.com')}"},
    )

    assert response.status_code == 403

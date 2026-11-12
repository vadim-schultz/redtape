"""The translation machine router: mounted inside the discovery machine router, so it shares its guards and handlers."""

from __future__ import annotations

from litestar import Router
from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.discovery.artifact_read import ArtifactReadService
from app.features.search.translation_subscriber import refresh_search_text_on_stored
from app.features.translation.admin_controller import TranslationAdminController
from app.features.translation.admin_service import TranslationAdminService
from app.features.translation.machine_controller import TranslationMachineController
from app.features.translation.queue import TranslationQueue
from app.features.translation.service import TranslationCompletion
from app.features.translation.snapshot_machine_controller import SnapshotMachineController
from app.features.translation.snapshot_queue import SnapshotQueue
from app.shared.object_store.http import InjectedObjectStore


def provide_translation_queue(session: Session) -> TranslationQueue:
    """Build the translation queue on the request session."""
    return TranslationQueue(session)


def provide_snapshot_queue(session: Session, discovery_artifact_read_service: ArtifactReadService) -> SnapshotQueue:
    """Build the snapshot queue on the request session, stamping claims from the discovery artifact reads."""
    return SnapshotQueue(session, discovery_artifact_read_service)


def provide_translation_completion(session: Session, object_store: InjectedObjectStore) -> TranslationCompletion:
    """Build the completion step on the request session and the ledger-metered object store (``None`` when unset)."""
    return TranslationCompletion(session, object_store, subscribers=(refresh_search_text_on_stored(session),))


def provide_translation_admin_service(session: Session) -> TranslationAdminService:
    """Build the admin coverage service on the request session."""
    return TranslationAdminService(session)


translation_machine_router = Router(
    path="/translations",
    route_handlers=[TranslationMachineController],
    dependencies={
        "translation_queue": Provide(provide_translation_queue, sync_to_thread=False),
        "translation_completion": Provide(provide_translation_completion, sync_to_thread=False),
    },
    tags=["translation-machine"],
)

snapshot_machine_router = Router(
    path="/snapshots",
    route_handlers=[SnapshotMachineController],
    dependencies={"snapshot_queue": Provide(provide_snapshot_queue, sync_to_thread=False)},
    tags=["translation-machine"],
)

translation_admin_router = Router(
    path="/api/v1/admin/translations",
    route_handlers=[TranslationAdminController],
    dependencies={"translation_admin_service": Provide(provide_translation_admin_service, sync_to_thread=False)},
    tags=["translation-admin"],
)

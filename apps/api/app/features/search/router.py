"""The embedding machine router: mounted inside the discovery machine router, so it shares its guards and handlers."""

from __future__ import annotations

from litestar import Router
from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.search.complete import EmbeddingCompletion
from app.features.search.machine_controller import EmbeddingMachineController
from app.features.search.queue import EmbeddingQueue


def provide_embedding_queue(session: Session) -> EmbeddingQueue:
    """Build the embedding queue on the request session."""
    return EmbeddingQueue(session)


def provide_embedding_completion(session: Session) -> EmbeddingCompletion:
    """Build the completion step on the request session."""
    return EmbeddingCompletion(session)


embedding_machine_router = Router(
    path="/embeddings",
    route_handlers=[EmbeddingMachineController],
    dependencies={
        "embedding_queue": Provide(provide_embedding_queue, sync_to_thread=False),
        "embedding_completion": Provide(provide_embedding_completion, sync_to_thread=False),
    },
    tags=["search-machine"],
)

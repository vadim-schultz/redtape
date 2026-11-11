"""The tunable numbers of one retrieval, read from settings once and passed to the legs and the fusion as values."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings


@dataclass(frozen=True, slots=True)
class RetrievalParams:
    """Fusion constant, leg and pool sizes, the cosine cut-off, the confidence weight, the model and the index switch."""

    rrf_k: int
    top_n: int
    fused_top_k: int
    min_similarity: float
    confidence_weight: float
    model: str
    vector_index_enabled: bool

    @classmethod
    def from_settings(cls, config: Settings) -> RetrievalParams:
        """Return the parameters ``config`` sets."""
        return cls(
            rrf_k=config.rrf_k,
            top_n=config.search_top_n,
            fused_top_k=config.search_fused_top_k,
            min_similarity=config.search_min_similarity,
            confidence_weight=config.search_confidence_weight,
            model=config.embedding_model,
            vector_index_enabled=config.search_vector_index_enabled,
        )

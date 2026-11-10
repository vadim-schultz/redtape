"""The displayed similarity: the cosine of a vector hit rescaled so the cut-off is 0 and a perfect match is 1."""

from __future__ import annotations


def rescaled_similarity(cosine: float | None, cutoff: float) -> float | None:
    """Return ``(cosine - cutoff) / (1 - cutoff)`` clipped to 0..1, or ``None`` without a cosine (no vector hit)."""
    if cosine is None:
        return None
    if cutoff >= 1.0:
        return 1.0 if cosine >= 1.0 else 0.0
    return min(max((cosine - cutoff) / (1.0 - cutoff), 0.0), 1.0)

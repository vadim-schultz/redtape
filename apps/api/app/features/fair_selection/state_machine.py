"""State machine for fair task selection priority formula and phase transitions.

Validates the design of the three-phase selection strategy:
- Phase 1 (Breadth-First): Every document gets ≥1 task per locale
- Phase 2 (Depth-First): Remaining work completed by confidence
- Phase 3 (Refresh): New versions re-enqueued

This module is design-only. It provides validators for the design logic.
Production implementation happens in C2–C10.
"""

from __future__ import annotations


class PhaseCoverage:
    """Tracks coverage bitmap for a document across locales.

    Uses a 64-bit integer bitmap where bit N represents locale N completion.
    Assumption: ≤64 locales.
    """

    def __init__(self, num_locales: int) -> None:
        """Initialize coverage tracker for a document.

        Args:
            num_locales: Number of locales (must be ≤ 64).
        """
        if num_locales > 64:
            raise ValueError("Coverage bitmap only supports ≤64 locales")
        self.num_locales = num_locales
        self.bitmap: int = 0

    def mark_complete(self, locale_index: int) -> None:
        """Mark a locale as complete.

        Args:
            locale_index: Zero-indexed locale position.
        """
        if not 0 <= locale_index < self.num_locales:
            raise ValueError(f"Locale index {locale_index} out of range [0, {self.num_locales})")
        self.bitmap |= 1 << locale_index

    def is_phase_complete(self) -> bool:
        """Check if all locales are complete (phase 1 → 2 trigger).

        Returns:
            True if all locales have been marked complete.
        """
        full_mask = (1 << self.num_locales) - 1
        return self.bitmap == full_mask


class StateMachine:
    """Phase-state machine for fair task selection.

    Tracks phase transitions (1 → 2 → 3) based on completion coverage.
    """

    def __init__(self, num_documents: int, num_locales: int) -> None:
        """Initialize state machine.

        Args:
            num_documents: Number of documents in workload.
            num_locales: Number of locales per document.
        """
        self.num_documents = num_documents
        self.num_locales = num_locales
        self.current_phase = 1
        self.phase_1_complete = False

        # Track coverage per document
        self._coverages: list[PhaseCoverage] = [
            PhaseCoverage(num_locales) for _ in range(num_documents)
        ]

    def settle_task(self, doc_index: int, locale_index: int) -> None:
        """Mark a task as settled (completed).

        Auto-transitions phase 1 → 2 if all documents complete.

        Args:
            doc_index: Zero-indexed document position.
            locale_index: Zero-indexed locale position.
        """
        if not 0 <= doc_index < self.num_documents:
            raise ValueError(f"Document index {doc_index} out of range [0, {self.num_documents})")

        self._coverages[doc_index].mark_complete(locale_index)

        # Check for phase 1 → 2 transition
        if not self.phase_1_complete and self._check_phase1_complete():
            self.current_phase = 2
            self.phase_1_complete = True

    def _check_phase1_complete(self) -> bool:
        """Check if all documents have ≥1 completed task per locale.

        Returns:
            True if all documents are phase 1 complete.
        """
        return all(cov.is_phase_complete() for cov in self._coverages)


def calculate_priority(
    *,
    phase: int,
    confidence: float,
    locale_index: int,
    candidate_id: str,  # For grouping in claim (not in formula)
) -> int:
    """Calculate priority score for task selection.

    Priority formula (unified across pipelines):
      priority = (phase_component * 100_000) + (confidence_rank * 100) + locale_index

    Where:
      phase_component = 0 if phase 1, 1 if phase 2, 2 if phase 3
      confidence_rank = 1000 - round(confidence * 1000)  (higher = lower priority)
      locale_index = 0–99 (stable tie-break within (phase, rank))

    Args:
        phase: Phase (1, 2, or 3).
        confidence: Confidence score (0.0–1.0).
        locale_index: Locale index for tie-breaking (0–99).
        candidate_id: Candidate ID (used for grouping, not in formula).

    Returns:
        Priority score (lower = claim sooner).
    """
    if not 1 <= phase <= 3:
        raise ValueError(f"Phase must be 1, 2, or 3; got {phase}")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"Confidence must be 0.0–1.0; got {confidence}")
    if not 0 <= locale_index <= 99:
        raise ValueError(f"Locale index must be 0–99; got {locale_index}")

    # Phase component: 0 for phase 1, 100_000 for phase 2, 200_000 for phase 3
    phase_component = (phase - 1) * 100_000

    # Confidence rank: 1000 - round(confidence * 1000)
    # (confidence=1.0 → rank=0, confidence=0.0 → rank=1000)
    confidence_rank = 1000 - round(confidence * 1000)

    # Priority formula
    priority = phase_component + (confidence_rank * 100) + locale_index

    return priority

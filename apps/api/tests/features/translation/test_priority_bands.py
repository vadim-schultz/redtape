"""Claim priorities keep each phase in its own band and first translations ahead of re-translations.

Confidences are sampled in thousandths over the whole 0.0–1.0 range, which is the resolution the rank uses.
"""

from __future__ import annotations

from app.features.translation.priority import first_priority, retranslation_priority, upgrade_priority

CONFIDENCES = tuple(step / 1000 for step in range(1001))
"""Every confidence in thousandths, from 0.0 to 1.0 inclusive."""


def test_a_phase_one_priority_never_reaches_phase_two() -> None:
    """Every phase-1 priority, of every task kind, sorts before every phase-2 priority."""
    phase_one = [
        *(first_priority(confidence, phase=1) for confidence in CONFIDENCES),
        *(retranslation_priority(confidence, phase=1) for confidence in CONFIDENCES),
        upgrade_priority(phase=1),
    ]
    phase_two = [
        *(first_priority(confidence, phase=2) for confidence in CONFIDENCES),
        *(retranslation_priority(confidence, phase=2) for confidence in CONFIDENCES),
        upgrade_priority(phase=2),
    ]
    assert max(phase_one) < min(phase_two), f"phase 1 reaches {max(phase_one)} but phase 2 starts at {min(phase_two)}"


def test_a_retranslation_never_outranks_a_first_translation() -> None:
    """Within one phase, every first translation sorts before every re-translation."""
    for phase in (1, 2, 3):
        firsts = [first_priority(confidence, phase=phase) for confidence in CONFIDENCES]
        retranslations = [retranslation_priority(confidence, phase=phase) for confidence in CONFIDENCES]
        # The largest first-translation value below the smallest re-translation value covers every pair.
        assert max(firsts) < min(retranslations), (
            f"phase {phase}: a first translation reaches {max(firsts)} but a re-translation starts at {min(retranslations)}"
        )

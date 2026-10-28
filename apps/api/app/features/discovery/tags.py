"""Tag consensus: which codes the procedures that mention a candidate agree on."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import NamedTuple
from uuid import UUID

DEFAULT_MIN_PROCEDURES = 2
DEFAULT_MIN_SHARE = 0.5

TaggedMention = tuple[UUID, Sequence[str] | None]
"""A mention as plain data: the procedure (catalogue row) it came from and the codes it carries."""


class TagSupport(NamedTuple):
    """How many procedures carry one code, their share of the tagged procedures, and whether that suffices."""

    code: str
    procedures: int
    share: float
    accepted: bool


def _procedures_by_code(mentions: Iterable[TaggedMention]) -> dict[str, set[UUID]]:
    by_code: dict[str, set[UUID]] = defaultdict(set)
    for procedure_id, codes in mentions:
        for code in codes or ():
            by_code[code].add(procedure_id)
    return by_code


def _support(code: str, procedures: int, tagged: int, min_procedures: int, min_share: float) -> TagSupport:
    share = procedures / tagged
    return TagSupport(code, procedures, share, procedures >= min_procedures and share >= min_share)


def aggregate_tags(
    mentions: Iterable[TaggedMention],
    min_procedures: int = DEFAULT_MIN_PROCEDURES,
    min_share: float = DEFAULT_MIN_SHARE,
) -> list[TagSupport]:
    """Return the support of every code, most supported first.

    A code is counted once per distinct procedure, however many mentions carry it. The share divides by the
    distinct procedures that carry any code, so untagged mentions do not dilute it. ``accepted`` needs both
    thresholds.
    """
    by_code = _procedures_by_code(mentions)
    tagged = len(set().union(*by_code.values()))
    supports = [_support(code, len(ids), tagged, min_procedures, min_share) for code, ids in by_code.items()]
    return sorted(supports, key=lambda support: (-support.procedures, support.code))

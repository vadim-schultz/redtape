"""Translate legacy taxonomy inputs and scores at the API boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from scripts.seed_data.taxonomy import LEGACY_CROSSWALK, SITUATION_GROUP_CODES, SITUATION_GROUPS

LegacyAxis = Literal["domain", "life_situation"]

_LEGACY_TARGETS: dict[tuple[LegacyAxis, str], tuple[str, ...]] = {
    (mapping.axis, mapping.source_code): mapping.target_codes
    for mapping in LEGACY_CROSSWALK
    if mapping.state == "mapped"
}
_GROUP_SITUATIONS = {
    group.code: tuple(code for code, group_code in SITUATION_GROUP_CODES.items() if group_code == group.code)
    for group in SITUATION_GROUPS
}


@dataclass(frozen=True, slots=True)
class LegacyTranslation:
    """Canonical targets and source values produced by one legacy filter."""

    domain_targets: tuple[str, ...]
    situation_targets: tuple[str, ...]
    domain_codes: tuple[str, ...]
    situation_codes: tuple[str, ...]


class LegacyTaxonomyAdapter:
    """Resolve the frozen domain, group, and situation compatibility crosswalk."""

    def translate(
        self,
        *,
        domain_codes: Sequence[str],
        group_codes: Sequence[str],
        situation_codes: Sequence[str],
    ) -> LegacyTranslation:
        """Translate legacy filters and reject unknown or conflicting values."""
        domains = self._mapped_codes("domain", domain_codes)
        situations = self._mapped_codes("life_situation", situation_codes)
        group_situations = self._group_situation_codes(group_codes)
        if group_situations and situation_codes and not set(group_situations) & set(situation_codes):
            raise ValueError("Conflicting legacy taxonomy filters: group and situation do not overlap")
        groups = self._mapped_codes("life_situation", group_situations)
        return LegacyTranslation(
            domain_targets=domains,
            situation_targets=(*situations, *groups),
            domain_codes=tuple(dict.fromkeys(domain_codes)),
            situation_codes=tuple(dict.fromkeys((*situation_codes, *group_situations))),
        )

    def source_codes_for_categories(self, codes: Sequence[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Return legacy source codes that can produce selected canonical categories."""
        domains: list[str] = []
        situations: list[str] = []
        selected = set(codes)
        for (axis, source_code), targets in _LEGACY_TARGETS.items():
            if not selected.isdisjoint(targets):
                (domains if axis == "domain" else situations).append(source_code)
        return tuple(domains), tuple(situations)

    def canonical_scores(
        self,
        *,
        domain_scores: Mapping[str, float],
        situation_scores: Mapping[str, float],
    ) -> dict[str, float]:
        """Translate legacy scored tags using the frozen maximum-confidence policy."""
        result: dict[str, float] = {}
        axes: tuple[tuple[LegacyAxis, Mapping[str, float]], ...] = (
            ("domain", domain_scores),
            ("life_situation", situation_scores),
        )
        for axis, scores in axes:
            for source_code, score in scores.items():
                for category_code in _LEGACY_TARGETS.get((axis, source_code), ()):
                    result[category_code] = max(score, result.get(category_code, 0.0))
        return result

    @staticmethod
    def _mapped_codes(axis: LegacyAxis, codes: Sequence[str]) -> tuple[str, ...]:
        """Translate mapped legacy values and reject unknown or unmapped values."""
        unknown = sorted({code for code in codes if (axis, code) not in _LEGACY_TARGETS})
        if unknown:
            raise ValueError(f"Unknown legacy {axis} code(s): {', '.join(unknown)}")
        return tuple(dict.fromkeys(target for code in codes for target in _LEGACY_TARGETS[(axis, code)]))

    @staticmethod
    def _group_situation_codes(codes: Sequence[str]) -> tuple[str, ...]:
        """Translate legacy groups to their contained legacy situation codes."""
        unknown = sorted(set(codes) - _GROUP_SITUATIONS.keys())
        if unknown:
            raise ValueError(f"Unknown legacy group code(s): {', '.join(unknown)}")
        return tuple(dict.fromkeys(code for group in codes for code in _GROUP_SITUATIONS[group]))

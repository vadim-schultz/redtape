"""The validated PVOG crosswalk that the machine taxonomy serves, and the evidence lookup it backs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from discovery_ingest.pvog.models import PvogSourcePath

CategoryEvidenceState = Literal["mapped", "review"]


class CrosswalkError(RuntimeError):
    """The machine taxonomy's crosswalk cannot be fetched, is malformed, or names a category it does not serve.

    It is not a ``ValueError``, so a validation that hits it propagates it instead of reporting it as a bad field.
    """


@dataclass(frozen=True, slots=True)
class PvogCategoryEvidence:
    """Canonical category evidence with the PVOG leaf and source path that support it."""

    leaf_code: str
    category_codes: tuple[str, ...]
    confidence: float
    state: CategoryEvidenceState
    reason: str
    mapping_version: str
    source_path: PvogSourcePath


@dataclass(frozen=True, slots=True)
class LeafEntry:
    """One validated PVOG leaf mapping as the crosswalk holds it."""

    category_codes: tuple[str, ...]
    confidence: float
    state: CategoryEvidenceState
    reason: str


@dataclass(frozen=True, slots=True)
class MachineCrosswalk:
    """A crosswalk whose sections have been validated against each other; ingest maps evidence through it only."""

    artifact_version: str
    pvog_source_version: str
    source_parents: Mapping[str, tuple[str, ...]]
    leaves: Mapping[str, LeafEntry]

    def evidence_for_path(self, path: PvogSourcePath) -> PvogCategoryEvidence | None:
        """Map a complete PVOG path to canonical evidence; never infer a category from a bare leaf."""
        if not path.has_parent_path or path.leaf_code is None:
            return None
        entry = self.leaves.get(path.leaf_code)
        if entry is None or not self._parent_is_source(path.parent_code, entry.category_codes):
            return None
        return PvogCategoryEvidence(
            leaf_code=path.leaf_code,
            category_codes=entry.category_codes,
            confidence=entry.confidence,
            state=entry.state,
            reason=entry.reason,
            mapping_version=self.artifact_version,
            source_path=path,
        )

    def _parent_is_source(self, parent_code: str | None, category_codes: tuple[str, ...]) -> bool:
        """Return whether ``parent_code`` is a PVOG source parent of at least one of ``category_codes``."""
        return any(parent_code in self.source_parents[code] for code in category_codes)

"""Parse and validate the machine taxonomy body into the crosswalk ingest maps evidence through."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import ValidationError

from discovery_ingest.json_types import JsonValue
from discovery_ingest.pvog.category_mapping import CrosswalkError, LeafEntry, MachineCrosswalk
from discovery_ingest.pvog.crosswalk_wire import ServedLeafMapping, ServedVocabulary


def parse_crosswalk(body: JsonValue) -> MachineCrosswalk:
    """Return the validated crosswalk of the machine taxonomy ``body``; raise :class:`CrosswalkError` when it is unusable."""
    vocabulary = _shape(body)
    crosswalk = vocabulary.crosswalk
    if not crosswalk.artifact_version.strip() or not crosswalk.pvog_source_version.strip():
        raise CrosswalkError("machine crosswalk names no artifact or source version")
    served = {category.code for category in vocabulary.categories}
    return MachineCrosswalk(
        artifact_version=crosswalk.artifact_version,
        pvog_source_version=crosswalk.pvog_source_version,
        source_parents={category.code: category.source_parent_codes for category in vocabulary.categories},
        leaves=_leaves(crosswalk.pvog_leaf_mappings, served),
    )


def _shape(body: JsonValue) -> ServedVocabulary:
    """Return ``body`` as the served vocabulary, or raise :class:`CrosswalkError` when its shape is wrong."""
    try:
        return ServedVocabulary.model_validate(body)
    except ValidationError as err:
        raise CrosswalkError(f"machine crosswalk is malformed: {err.error_count()} errors") from err


def _leaves(mappings: Sequence[ServedLeafMapping], served: set[str]) -> dict[str, LeafEntry]:
    """Index the PVOG leaf mappings by leaf code, refusing a repeated leaf or a target that is not served."""
    if not mappings:
        raise CrosswalkError("machine crosswalk has no PVOG leaf mappings")
    index: dict[str, LeafEntry] = {}
    for mapping in mappings:
        if mapping.leaf_code in index:
            raise CrosswalkError(f"duplicate PVOG leaf mapping: {mapping.leaf_code}")
        _check_targets(f"PVOG leaf {mapping.leaf_code}", mapping.category_codes, served)
        _check_reason(f"PVOG leaf {mapping.leaf_code}", mapping.reason)
        index[mapping.leaf_code] = LeafEntry(mapping.category_codes, mapping.confidence, mapping.state, mapping.reason)
    return index


def _check_targets(owner: str, codes: tuple[str, ...], served: set[str]) -> None:
    """Refuse a mapping with no target, or with a target the served vocabulary does not contain."""
    if not codes:
        raise CrosswalkError(f"{owner} maps to no category")
    unserved = sorted(code for code in codes if code not in served)
    if unserved:
        raise CrosswalkError(f"{owner} names categories the vocabulary does not serve: {', '.join(unserved)}")


def _check_reason(owner: str, reason: str) -> None:
    """Refuse a mapping that does not say why it maps."""
    if not reason.strip():
        raise CrosswalkError(f"{owner} has no reason")

"""Write the discovery machine contract fixture that the ingest contract tests compare against.

Run from ``apps/api``::

    uv run python -m scripts.export_machine_contract

The fixture holds the machine routes from the OpenAPI document, the JSON Schema of every model that
the ingest package mirrors (request models in validation mode, response models in serialization
mode), the value lists of the wire enums, and the field names of the artifact upload form.
``tests/test_machine_contract_fixture.py`` fails when the committed file is stale.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Literal, get_args

from app.features.discovery.budget_resources import BudgetResource
from app.features.taxonomy.crosswalk import contract_vocabulary
from app.main import create_app
from app.models.discovery import (
    LEGACY_TASK_KINDS,
    DiscoveryArtifactKind,
    DiscoveryClaimKind,
    DiscoveryEdgeBasis,
    DiscoveryMentionRole,
    DiscoveryRunKind,
    DiscoverySource,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.search import WorkTaskStatus
from app.schema.discovery import (
    artifacts,
    budgets,
    candidate_edges,
    candidate_emit,
    candidate_sources,
    candidates,
    machine,
    read,
)
from app.schema.search import machine as search_machine
from app.schema.taxonomy import read as taxonomy_read
from app.schema.translation import machine as translation_machine
from app.shared.taxonomy.contract_loader import load_contract
from pydantic import BaseModel

REGENERATE_COMMAND = "python -m scripts.export_machine_contract"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "discovery_machine_contract.json"
VOCABULARY_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "machine_vocabulary.json"
MACHINE_PREFIX = "/api/v1/discovery/machine"
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete"})

Mode = Literal["validation", "serialization"]

MODELS: dict[str, tuple[type[BaseModel], Mode]] = {
    # Requests the ingest package sends: validated by the API.
    "machine.CatalogueBatchItem": (machine.CatalogueBatchItem, "validation"),
    "machine.CatalogueBatchRequest": (machine.CatalogueBatchRequest, "validation"),
    "machine.EntityUpsertRequest": (machine.EntityUpsertRequest, "validation"),
    "machine.ClaimAppendRequest": (machine.ClaimAppendRequest, "validation"),
    "machine.TaskClaimRequest": (machine.TaskClaimRequest, "validation"),
    "machine.TaskEnqueueRequest": (machine.TaskEnqueueRequest, "validation"),
    "machine.FetchLogAppendRequest": (machine.FetchLogAppendRequest, "validation"),
    "machine.RunFinishRequest": (machine.RunFinishRequest, "validation"),
    "machine.RunStartRequest": (machine.RunStartRequest, "validation"),
    "machine.TaskCompleteRequest": (machine.TaskCompleteRequest, "validation"),
    "machine.TaskReleaseRequest": (machine.TaskReleaseRequest, "validation"),
    "machine.TaskFailRequest": (machine.TaskFailRequest, "validation"),
    "candidates.CandidateMentionItem": (candidates.CandidateMentionItem, "validation"),
    "candidates.CandidateMentionsRequest": (candidates.CandidateMentionsRequest, "validation"),
    "candidate_edges.CandidateEdgeItem": (candidate_edges.CandidateEdgeItem, "validation"),
    "candidate_edges.CandidateEdgesRequest": (candidate_edges.CandidateEdgesRequest, "validation"),
    "candidate_emit.CandidateEmitRequest": (candidate_emit.CandidateEmitRequest, "validation"),
    "budgets.BudgetReserveRequest": (budgets.BudgetReserveRequest, "validation"),
    "budgets.BudgetAdjustRequest": (budgets.BudgetAdjustRequest, "validation"),
    "search_machine.EmbeddingClaimRequest": (search_machine.EmbeddingClaimRequest, "validation"),
    "search_machine.EmbeddingCompleteItem": (search_machine.EmbeddingCompleteItem, "validation"),
    "search_machine.EmbeddingCompleteRequest": (search_machine.EmbeddingCompleteRequest, "validation"),
    "search_machine.EmbeddingFailRequest": (search_machine.EmbeddingFailRequest, "validation"),
    "search_machine.EmbeddingReleaseRequest": (search_machine.EmbeddingReleaseRequest, "validation"),
    "translation_machine.TranslationClaimRequest": (translation_machine.TranslationClaimRequest, "validation"),
    "translation_machine.TranslationCompleteItem": (translation_machine.TranslationCompleteItem, "validation"),
    "translation_machine.TranslationCompleteRequest": (translation_machine.TranslationCompleteRequest, "validation"),
    "translation_machine.TranslationFailRequest": (translation_machine.TranslationFailRequest, "validation"),
    "translation_machine.TranslationReleaseRequest": (translation_machine.TranslationReleaseRequest, "validation"),
    # Responses the ingest package validates: serialized by the API.
    "machine.CatalogueMachineRead": (machine.CatalogueMachineRead, "serialization"),
    "machine.EntityUpsertResponse": (machine.EntityUpsertResponse, "serialization"),
    "machine.ClaimAppendResponse": (machine.ClaimAppendResponse, "serialization"),
    "machine.TaskClaimResponse": (machine.TaskClaimResponse, "serialization"),
    "machine.ClaimedTaskRead": (machine.ClaimedTaskRead, "serialization"),
    "machine.TaskSummaryResponse": (machine.TaskSummaryResponse, "serialization"),
    "machine.TaskEnqueueResponse": (machine.TaskEnqueueResponse, "serialization"),
    "machine.RunRead": (machine.RunRead, "serialization"),
    "artifacts.ArtifactRead": (artifacts.ArtifactRead, "serialization"),
    "artifacts.ArtifactListResponse": (artifacts.ArtifactListResponse, "serialization"),
    "artifacts.ArtifactStatusResponse": (artifacts.ArtifactStatusResponse, "serialization"),
    "candidates.CandidateMentionsResponse": (candidates.CandidateMentionsResponse, "serialization"),
    "candidate_edges.CandidateEdgesResponse": (candidate_edges.CandidateEdgesResponse, "serialization"),
    "candidate_edges.EdgeSkip": (candidate_edges.EdgeSkip, "serialization"),
    "candidate_emit.CandidateEmitResponse": (candidate_emit.CandidateEmitResponse, "serialization"),
    "candidate_emit.CandidateEmitItemResult": (candidate_emit.CandidateEmitItemResult, "serialization"),
    "candidate_emit.EmitConflictRead": (candidate_emit.EmitConflictRead, "serialization"),
    "candidate_emit.CandidateEmitPreview": (candidate_emit.CandidateEmitPreview, "serialization"),
    "read.CandidateListResponse": (read.CandidateListResponse, "serialization"),
    "read.CandidateListItemRead": (read.CandidateListItemRead, "serialization"),
    "budgets.BudgetRead": (budgets.BudgetRead, "serialization"),
    "budgets.BudgetListResponse": (budgets.BudgetListResponse, "serialization"),
    "budgets.BudgetReserveResponse": (budgets.BudgetReserveResponse, "serialization"),
    "candidate_sources.CandidateSourceRead": (candidate_sources.CandidateSourceRead, "serialization"),
    "candidate_sources.CandidateSourceListResponse": (candidate_sources.CandidateSourceListResponse, "serialization"),
    "taxonomy_read.VocabularyTerm": (taxonomy_read.VocabularyTerm, "serialization"),
    "taxonomy_read.VocabularyResponse": (taxonomy_read.VocabularyResponse, "serialization"),
    "taxonomy_read.CrosswalkRead": (taxonomy_read.CrosswalkRead, "serialization"),
    "taxonomy_read.PvogLeafMappingRead": (taxonomy_read.PvogLeafMappingRead, "serialization"),
    "search_machine.EmbeddingClaimResponse": (search_machine.EmbeddingClaimResponse, "serialization"),
    "search_machine.ClaimedEmbeddingTask": (search_machine.ClaimedEmbeddingTask, "serialization"),
    "search_machine.EmbeddingCompleteResponse": (search_machine.EmbeddingCompleteResponse, "serialization"),
    "search_machine.EmbeddingItemResult": (search_machine.EmbeddingItemResult, "serialization"),
    "search_machine.EmbeddingFailResponse": (search_machine.EmbeddingFailResponse, "serialization"),
    "search_machine.EmbeddingReleaseResponse": (search_machine.EmbeddingReleaseResponse, "serialization"),
    "search_machine.EmbeddingSummaryResponse": (search_machine.EmbeddingSummaryResponse, "serialization"),
    "translation_machine.TranslationClaimResponse": (translation_machine.TranslationClaimResponse, "serialization"),
    "translation_machine.ClaimedTranslationTask": (translation_machine.ClaimedTranslationTask, "serialization"),
    "translation_machine.TranslationCompleteResponse": (
        translation_machine.TranslationCompleteResponse,
        "serialization",
    ),
    "translation_machine.TranslationItemResult": (translation_machine.TranslationItemResult, "serialization"),
    "translation_machine.TranslationFailResponse": (translation_machine.TranslationFailResponse, "serialization"),
    "translation_machine.TranslationReleaseResponse": (translation_machine.TranslationReleaseResponse, "serialization"),
    "translation_machine.TranslationSummaryResponse": (translation_machine.TranslationSummaryResponse, "serialization"),
    "translation_machine.TranslationLocaleSummary": (translation_machine.TranslationLocaleSummary, "serialization"),
}
"""Every model the contract covers, with the mode the wire uses: requests validate, responses serialize."""


def _values(enum_cls: type[StrEnum]) -> list[str]:
    """Return the member values of a string enum in declaration order."""
    return [str(member.value) for member in enum_cls]


ENUMS: dict[str, list[str]] = {
    "DiscoverySource": _values(DiscoverySource),
    "DiscoveryTaskKind": _values(DiscoveryTaskKind),
    "DiscoveryTaskStatus": _values(DiscoveryTaskStatus),
    "DiscoveryClaimKind": _values(DiscoveryClaimKind),
    "DiscoveryMentionRole": _values(DiscoveryMentionRole),
    "DiscoveryArtifactKind": _values(DiscoveryArtifactKind),
    "DiscoveryEdgeBasis": _values(DiscoveryEdgeBasis),
    "DiscoveryRunKind": _values(DiscoveryRunKind),
    "BudgetResource": _values(BudgetResource),
    "LEGACY_TASK_KINDS": [str(kind.value) for kind in LEGACY_TASK_KINDS],
    "EmbeddingOutcome": _values(search_machine.EmbeddingOutcome),
    "TranslationOutcome": _values(translation_machine.TranslationOutcome),
    "WorkTaskStatus": _values(WorkTaskStatus),
    "StopReason": list(get_args(machine.StopReason)),
    "EdgeSkipReason": list(get_args(candidate_edges.EdgeSkipReason)),
}
"""Value lists of the wire enums, in the order the API declares them."""

FORMS: dict[str, list[str]] = {
    "ArtifactUploadForm": [field.name for field in dataclasses.fields(artifacts.ArtifactUploadForm)],
}
"""Field names of multipart form dataclasses, which have no Pydantic schema."""


def exported_schema(key: str) -> dict[str, object]:
    """Return the JSON Schema of the model named ``key`` in its wire mode; unknown keys raise ``KeyError``.

    A serialized response always carries every field, defaulted ones included, so in serialization
    mode every top-level property is marked required. Pydantic only does this for models that opt in
    through ``json_schema_serialization_defaults_required``, and the API models do not.
    """
    model, mode = MODELS[key]
    schema = model.model_json_schema(mode=mode)
    if mode == "serialization":
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            schema["required"] = sorted(properties)
    return schema


def machine_routes() -> list[dict[str, str]]:
    """Return every method and path under the machine prefix, from the generated OpenAPI document."""
    paths = create_app().openapi_schema.to_schema()["paths"]
    routes = [
        {"method": method.upper(), "path": path}
        for path, operations in paths.items()
        if path.startswith(MACHINE_PREFIX)
        for method in operations
        if method in HTTP_METHODS
    ]
    return sorted(routes, key=lambda route: (route["path"], route["method"]))


def contract_document() -> dict[str, object]:
    """Assemble the fixture document from the routes, models, enums and forms."""
    models: dict[str, object] = {
        key: {"mode": mode, "schema": exported_schema(key)} for key, (_model, mode) in MODELS.items()
    }
    return {
        "generated_by": REGENERATE_COMMAND,
        "routes": machine_routes(),
        "models": models,
        "enums": ENUMS,
        "forms": FORMS,
    }


def _as_text(document: Mapping[str, object]) -> str:
    """Return a fixture document as stable, indented JSON with a trailing newline."""
    return json.dumps(document, indent=1, sort_keys=True) + "\n"


def render_contract() -> str:
    """Return the fixture as stable, indented JSON with a trailing newline."""
    return _as_text(contract_document())


def render_vocabulary() -> str:
    """Return the served vocabulary the artifact yields by itself, as stable indented JSON with a trailing newline.

    The ingest tests read it as the machine crosswalk; it needs no database, so the export runs anywhere.
    """
    return _as_text(contract_vocabulary(load_contract()).model_dump(mode="json"))


def main() -> None:
    """Write the fixture files and print their paths."""
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(render_contract(), encoding="utf-8")
    VOCABULARY_PATH.write_text(render_vocabulary(), encoding="utf-8")
    print(f"wrote {FIXTURE_PATH}")
    print(f"wrote {VOCABULARY_PATH}")


if __name__ == "__main__":
    main()

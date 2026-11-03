"""Structural guards for the suggestion core: no submitter switch, typed dispatch, no dead parameters."""

from __future__ import annotations

import inspect
import uuid
from pathlib import Path
from unittest.mock import Mock

import pytest
from app.features.suggestions.filters import SuggestionFilters
from app.features.suggestions.handlers import (
    HandlerDeps,
    KindDispatch,
    NewDocumentHandler,
    PayloadKindMismatchError,
)
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import SuggestionService
from app.features.suggestions.transitions import SuggestionTransitions
from app.schema.suggestion.payload import NewRequirementPayload

SERVICE_PATH = Path(__file__).resolve().parent.parent / "app" / "features" / "suggestions" / "service.py"


def test_service_has_no_submitter_kind_switch() -> None:
    text = SERVICE_PATH.read_text(encoding="utf-8")

    assert ".kind ==" not in text
    assert "SubmitterRef" not in text


def test_kind_dispatch_rejects_payload_of_the_wrong_kind() -> None:
    dispatch = KindDispatch(NewDocumentHandler(HandlerDeps(documents=Mock(), taxonomy=Mock(), suggestions=Mock())))
    payload = NewRequirementPayload(parent_document_id=uuid.uuid4(), required_document_id=uuid.uuid4())

    with pytest.raises(PayloadKindMismatchError):
        dispatch.validate(payload, jurisdiction_id=uuid.uuid4())


def test_transition_to_has_no_reason_parameter() -> None:
    assert "reason" not in inspect.signature(SuggestionService.transition_to).parameters
    assert "reason" not in inspect.signature(SuggestionTransitions.transition_to).parameters


def test_filters_module_owns_suggestion_filters() -> None:
    assert SuggestionFilters.__module__ == "app.features.suggestions.filters"


def test_repository_takes_the_filters_value_as_one_argument() -> None:
    assert list(inspect.signature(SuggestionRepository.count).parameters) == ["self", "filters"]
    list_page = list(inspect.signature(SuggestionRepository.list_page).parameters)
    assert list_page[:4] == ["self", "filters", "offset", "limit"]

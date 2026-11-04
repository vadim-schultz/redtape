"""The directional comparator fails on each drift it is meant to catch, and passes what it should pass."""

from __future__ import annotations

from typing import Literal

from discovery_ingest.json_types import JsonObject
from pydantic import BaseModel, Field

from contract_compare import body_problems, compare


def _request(model: type[BaseModel]) -> JsonObject:
    return model.model_json_schema(mode="validation")


def _response(model: type[BaseModel]) -> JsonObject:
    schema = model.model_json_schema(mode="serialization")
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        schema["required"] = sorted(properties)
    return schema


def test_identical_schemas_and_a_subset_read_pass() -> None:
    """comparator · identical request schemas and a response that reads fewer fields both pass."""

    class Api(BaseModel):
        name: str = Field(min_length=1, max_length=20)
        count: int = Field(default=0, ge=0)

    class IngestSame(BaseModel):
        name: str = Field(min_length=1, max_length=20)
        count: int = Field(default=0, ge=0)

    class IngestSubset(BaseModel):
        id: int

    class ApiRead(BaseModel):
        id: int
        extra: str

    assert compare(_request(IngestSame), _request(Api), "request") == []
    assert compare(_request(IngestSubset), _request(ApiRead), "response") == []


def test_a_new_api_enum_value_fails_a_response_pair() -> None:
    """comparator · a value the API can now send that ingest does not accept is a response problem."""

    class Api(BaseModel):
        status: Literal["pending", "claimed", "completed"]

    class Ingest(BaseModel):
        status: Literal["pending", "claimed"]

    problems = compare(_request(Ingest), _response(Api), "response")
    assert any("status" in problem and "completed" in problem for problem in problems), problems


def test_a_new_ingest_enum_value_fails_a_request_pair() -> None:
    """comparator · a value ingest sends that the API rejects is a request problem."""

    class Api(BaseModel):
        status: Literal["pending", "claimed"]

    class Ingest(BaseModel):
        status: Literal["pending", "claimed", "stuck"]

    problems = compare(_request(Ingest), _request(Api), "request")
    assert any("status" in problem and "stuck" in problem for problem in problems), problems


def test_an_api_required_field_missing_in_ingest_fails_a_request_pair() -> None:
    """comparator · a field the API requires that ingest never sends is a request problem."""

    class Api(BaseModel):
        name: str
        kind: str

    class Ingest(BaseModel):
        name: str

    problems = compare(_request(Ingest), _request(Api), "request")
    assert any(problem.startswith("kind:") for problem in problems), problems


def test_an_api_required_field_with_a_null_default_in_ingest_fails_a_request_pair() -> None:
    """comparator · a required API field that ingest may leave as null is a request problem."""

    class Api(BaseModel):
        kind: str

    class Ingest(BaseModel):
        kind: str | None = None

    problems = compare(_request(Ingest), _request(Api), "request")
    assert any(problem.startswith("kind:") for problem in problems), problems


def test_an_ingest_field_unknown_to_the_api_fails() -> None:
    """comparator · a field ingest sends that the API does not know is silently dropped, so it is drift."""

    class Api(BaseModel):
        name: str

    class Ingest(BaseModel):
        name: str
        colour: str

    problems = compare(_request(Ingest), _request(Api), "request")
    assert any(problem.startswith("colour:") for problem in problems), problems


def test_a_looser_ingest_bound_fails_a_request_pair() -> None:
    """comparator · an ingest bound that admits more than the API admits is a request problem."""

    class Api(BaseModel):
        error_detail: str | None = Field(default=None, max_length=1000)

    class Ingest(BaseModel):
        error_detail: str | None = None

    problems = compare(_request(Ingest), _request(Api), "request")
    assert any(problem.startswith("error_detail:") and "maxLength" in problem for problem in problems), problems


def test_a_stricter_ingest_bound_passes_a_request_pair() -> None:
    """comparator · an ingest bound at least as strict as the API bound is compatible."""

    class Api(BaseModel):
        claimed: int = Field(ge=0)

    class Ingest(BaseModel):
        claimed: int = Field(ge=1)

    assert compare(_request(Ingest), _request(Api), "request") == []


def test_a_nullable_api_field_must_be_nullable_in_ingest() -> None:
    """comparator · a response the API may send as null must be a nullable field in ingest."""

    class Api(BaseModel):
        label: str | None

    class Ingest(BaseModel):
        label: str

    problems = compare(_request(Ingest), _response(Api), "response")
    assert any(problem.startswith("label:") and "null" in problem for problem in problems), problems


def test_an_ingest_required_field_the_api_may_omit_fails_a_response_pair() -> None:
    """comparator · a response field ingest requires, which the API serializes only sometimes, is a problem."""

    class Api(BaseModel):
        note: str | None = None

    class Ingest(BaseModel):
        note: str | None

    problems = compare(_request(Ingest), _request(Api), "response")
    assert any(problem.startswith("note:") and "omit" in problem for problem in problems), problems


def test_a_response_default_is_always_present() -> None:
    """comparator · a defaulted response field counts as present, because the API always serializes it."""

    class Api(BaseModel):
        note: str | None = None

    class Ingest(BaseModel):
        note: str | None = None

    assert compare(_request(Ingest), _response(Api), "response") == []


def test_an_enum_override_supplies_the_api_value_set_for_a_bare_string() -> None:
    """comparator · a field the API types as a bare string is checked against the override value set."""

    class Api(BaseModel):
        resource: str

    class Ingest(BaseModel):
        resource: Literal["neurons", "browser_seconds"]

    assert compare(_request(Ingest), _response(Api), "response", {"resource": ["neurons", "browser_seconds"]}) == []
    problems = compare(_request(Ingest), _response(Api), "response", {"resource": ["neurons", "r2_class_a"]})
    assert any(problem.startswith("resource:") and "r2_class_a" in problem for problem in problems), problems


def test_a_recorded_body_with_an_unknown_key_fails() -> None:
    """body check · a key the API request model does not declare fails, and a missing required key fails."""

    class Api(BaseModel):
        kind: Literal["worker_drain"]
        note: str | None = None

    schema = _request(Api)
    assert body_problems({"kind": "worker_drain"}, schema) == []
    assert any("colour" in problem for problem in body_problems({"kind": "worker_drain", "colour": "red"}, schema))
    assert any("kind" in problem for problem in body_problems({"note": None}, schema))
    assert any("stuck" in problem for problem in body_problems({"kind": "stuck"}, schema))

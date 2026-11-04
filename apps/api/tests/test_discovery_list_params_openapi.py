"""Pins the query parameter names of the discovery list routes in the OpenAPI schema (chapter B5)."""

from __future__ import annotations

from app.main import create_app

EXPECTED_QUERY_PARAMETERS = {
    "/api/v1/discovery/admin/candidates": ["limit", "min_mentions", "offset", "role", "sort", "source", "status"],
    "/api/v1/discovery/admin/tasks": ["kind", "limit", "offset", "source", "status"],
    "/api/v1/discovery/admin/catalogue": ["limit", "offset", "source"],
    "/api/v1/discovery/machine/candidates": ["limit", "min_mentions", "offset", "status"],
    "/api/v1/discovery/machine/candidates/sources": [
        "candidate_id",
        "catalogue_service_id",
        "host",
        "limit",
        "missing",
        "offset",
    ],
    "/api/v1/discovery/machine/artifacts": ["host", "kind", "limit", "offset"],
}


def _query_parameter_names(path: str) -> list[str]:
    schema = create_app().openapi_schema.to_schema()
    operation = schema["paths"][path]["get"]
    return sorted(p["name"] for p in operation.get("parameters", []) if p.get("in") == "query")


def test_discovery_list_endpoints_expose_the_same_query_parameter_names() -> None:
    actual = {path: _query_parameter_names(path) for path in EXPECTED_QUERY_PARAMETERS}

    assert actual == EXPECTED_QUERY_PARAMETERS

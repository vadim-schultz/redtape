"""The discovery machine contract fixture that the ingest contract tests read is current with the API models."""

from __future__ import annotations

import json

import pytest
from scripts import export_machine_contract as exporter

MACHINE_PATH_PREFIX = "/api/v1/discovery/machine"


def _checked_in() -> dict[str, object]:
    loaded: dict[str, object] = json.loads(exporter.FIXTURE_PATH.read_text(encoding="utf-8"))
    return loaded


def test_the_checked_in_fixture_is_current() -> None:
    """machine contract fixture · matches a fresh export of the API models, routes and enums."""
    assert exporter.FIXTURE_PATH.exists(), f"missing {exporter.FIXTURE_PATH}; run: {exporter.REGENERATE_COMMAND}"
    assert exporter.FIXTURE_PATH.read_text(encoding="utf-8") == exporter.render_contract(), (
        f"stale {exporter.FIXTURE_PATH}; run: {exporter.REGENERATE_COMMAND}"
    )


def test_every_route_in_the_fixture_is_under_the_machine_prefix() -> None:
    """machine contract fixture · routes are the machine routes and nothing else."""
    routes = _checked_in()["routes"]
    assert isinstance(routes, list)
    assert routes, "the machine route table must not be empty"
    for route in routes:
        assert isinstance(route, dict)
        assert str(route["path"]).startswith(MACHINE_PATH_PREFIX), route


def test_every_paired_model_is_exported() -> None:
    """machine contract fixture · every exported key resolves; an unknown key is refused."""
    models = _checked_in()["models"]
    assert isinstance(models, dict)
    assert set(models) == set(exporter.MODELS)
    for key in models:
        assert exporter.exported_schema(key)
    with pytest.raises(KeyError):
        exporter.exported_schema("machine.NoSuchModel")

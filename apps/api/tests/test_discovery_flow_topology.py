"""The pipeline topology covers every task kind and run stage, so a new kind fails the build."""

from __future__ import annotations

from app.features.discovery.flow.topology import EDGES, STAGES
from app.models.discovery import DiscoveryRunStage, DiscoveryTaskKind


def test_every_task_kind_and_run_stage_appears_in_the_topology() -> None:
    covered_kinds = {kind for stage in STAGES for kind in stage.task_kinds}
    covered_run_stages = {stage.run_stage for stage in STAGES}

    assert covered_kinds == set(DiscoveryTaskKind)
    assert covered_run_stages == set(DiscoveryRunStage)


def test_stage_ids_are_unique_and_every_edge_names_known_stages() -> None:
    ids = [stage.id for stage in STAGES]
    known = set(ids)

    assert len(ids) == len(known)
    assert all(edge.source in known and edge.target in known for edge in EDGES)

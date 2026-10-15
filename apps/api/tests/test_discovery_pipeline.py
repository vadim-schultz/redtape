"""Unit tests for discovery pipeline stage derivation."""

from __future__ import annotations

from app.features.discovery.pipeline import PipelineStageInput, derive_pipeline_stage


def test_derive_pipeline_stage_returns_t1_when_task_pending() -> None:
    stage = derive_pipeline_stage(
        PipelineStageInput(
            task_count=1,
            has_fetch_log=False,
            claim_count=0,
            all_emit_claims_resolvable=False,
        )
    )

    assert stage == "T1"


def test_derive_pipeline_stage_returns_t0_when_no_tasks() -> None:
    stage = derive_pipeline_stage(
        PipelineStageInput(
            task_count=0,
            has_fetch_log=False,
            claim_count=0,
            all_emit_claims_resolvable=False,
        )
    )

    assert stage == "T0"


def test_derive_pipeline_stage_returns_t2_when_fetch_logged() -> None:
    stage = derive_pipeline_stage(
        PipelineStageInput(
            task_count=1,
            has_fetch_log=True,
            claim_count=0,
            all_emit_claims_resolvable=False,
        )
    )

    assert stage == "T2"

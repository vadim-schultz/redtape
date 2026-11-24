"""The daily pipeline: the plan from queue summaries and budgets, and the three-phase run of its stages."""

from discovery_ingest.operations.pipeline.deadline import RUN_CEILING_SECONDS, stage_seconds
from discovery_ingest.operations.pipeline.plan import OmittedStage, PipelinePlan, PlanFacts, build_plan
from discovery_ingest.operations.pipeline.process import spawn_stage
from discovery_ingest.operations.pipeline.reader import PlanContext, read_plan_facts
from discovery_ingest.operations.pipeline.report import PipelineReport, StageRecord, publish_to_step_summary
from discovery_ingest.operations.pipeline.runner import PipelinePorts, run_pipeline
from discovery_ingest.operations.pipeline.signals import StageRegistry
from discovery_ingest.operations.pipeline.stages import FIRST_PASS, STAGES, stage_by_id

__all__ = [
    "FIRST_PASS",
    "RUN_CEILING_SECONDS",
    "STAGES",
    "OmittedStage",
    "PipelinePlan",
    "PipelinePorts",
    "PipelineReport",
    "PlanContext",
    "PlanFacts",
    "StageRecord",
    "StageRegistry",
    "build_plan",
    "publish_to_step_summary",
    "read_plan_facts",
    "run_pipeline",
    "spawn_stage",
    "stage_by_id",
    "stage_seconds",
]

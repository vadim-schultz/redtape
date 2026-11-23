"""The ports of ``pipeline``: the plan context from the settings, and the live ports a real run takes."""

from __future__ import annotations

import time
from functools import partial

import typer

from discovery_ingest.cli.context import api_client, settings_of
from discovery_ingest.operations.pipeline import (
    PipelinePorts,
    PlanContext,
    StageRegistry,
    publish_to_step_summary,
    read_plan_facts,
    spawn_stage,
)
from discovery_ingest.translation.settings import load_translation_settings


def plan_context(ctx: typer.Context) -> PlanContext:
    """Return the reader's settings: the embedding and LLM models, the neuron reserve, and no tail locales yet."""
    settings = settings_of(ctx)
    return PlanContext(
        embedding_model=settings.embedding_model,
        query_embed_reserve=load_translation_settings().query_embed_reserve,
        tail_locales=(),
        llm_model=settings.llm_model,
    )


def live_ports(ctx: typer.Context) -> PipelinePorts:
    """Return the ports a real run uses: the API reads, the stage processes, the monotonic clock and the step summary."""
    client = api_client(ctx)
    context = plan_context(ctx)
    summary_path = settings_of(ctx).github_step_summary
    return PipelinePorts(
        read_facts=partial(read_plan_facts, client, context),
        spawn=spawn_stage,
        clock=time.monotonic,
        registry=StageRegistry(),
        publish=partial(publish_to_step_summary, path=summary_path),
    )

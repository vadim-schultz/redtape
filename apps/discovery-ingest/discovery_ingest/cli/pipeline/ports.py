"""The plan context of ``pipeline``: the settings the plan reads, built from the ingest settings."""

from __future__ import annotations

import typer

from discovery_ingest.cli.context import settings_of
from discovery_ingest.operations.pipeline import PlanContext
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

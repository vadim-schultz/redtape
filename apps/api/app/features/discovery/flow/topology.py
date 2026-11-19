"""The static topology of the discovery pipeline: the stages, what each reads and writes, and how they feed each other.

Data only. The state rules in :mod:`app.features.discovery.flow.state` read it, and nothing here touches the database.
Cadences are the hours between the scheduled runs that drain each stage (the workflow crons).
"""

from __future__ import annotations

from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.flow.stage import Edge, FlowQueue, Stage
from app.models.discovery import DiscoveryRunStage, DiscoveryTaskKind

DAILY_CADENCE_HOURS = 24.0
"""One scheduled drain a day, the cron of every daily workflow."""
TWICE_DAILY_CADENCE_HOURS = 12.0
"""Two scheduled drains a day (the embedding cron runs at 06:10 and 18:10 UTC)."""

STAGES: tuple[Stage, ...] = (
    Stage(
        id="seed",
        label="Seed",
        task_kinds=(DiscoveryTaskKind.FETCH_URL, DiscoveryTaskKind.ENRICH_METADATA, DiscoveryTaskKind.HARVEST_PAYLOAD),
        queue=None,
        run_stage=DiscoveryRunStage.WORKER_DRAIN,
        allotment=BudgetResource.R2_CLASS_A,
        cadence_hours=DAILY_CADENCE_HOURS,
    ),
    Stage(
        id="render",
        label="Render",
        task_kinds=(DiscoveryTaskKind.RENDER_PAGE,),
        queue=None,
        run_stage=DiscoveryRunStage.WORKER_DRAIN,
        allotment=BudgetResource.BROWSER_SECONDS,
        cadence_hours=DAILY_CADENCE_HOURS,
    ),
    Stage(
        id="extract_page",
        label="Extract (rules)",
        task_kinds=(DiscoveryTaskKind.EXTRACT_PAGE,),
        queue=None,
        run_stage=DiscoveryRunStage.WORKER_DRAIN,
        allotment=None,
        cadence_hours=DAILY_CADENCE_HOURS,
    ),
    Stage(
        id="llm",
        label="Extract (LLM)",
        task_kinds=(DiscoveryTaskKind.LLM_EXTRACT,),
        queue=None,
        run_stage=DiscoveryRunStage.WORKER_DRAIN,
        allotment=BudgetResource.NEURONS,
        cadence_hours=DAILY_CADENCE_HOURS,
    ),
    Stage(
        id="capture",
        label="Screenshot",
        task_kinds=(DiscoveryTaskKind.CAPTURE_SCREENSHOT,),
        queue=None,
        run_stage=DiscoveryRunStage.WORKER_DRAIN,
        allotment=BudgetResource.BROWSER_SECONDS,
        cadence_hours=DAILY_CADENCE_HOURS,
    ),
    Stage(
        id="embed",
        label="Embed",
        task_kinds=(),
        queue=FlowQueue.EMBEDDING,
        run_stage=DiscoveryRunStage.EMBED,
        allotment=BudgetResource.NEURONS,
        cadence_hours=TWICE_DAILY_CADENCE_HOURS,
    ),
    Stage(
        id="card_translation",
        label="Card translation",
        task_kinds=(),
        queue=FlowQueue.CARD_TRANSLATION,
        run_stage=DiscoveryRunStage.TRANSLATE,
        allotment=BudgetResource.AZURE_TRANSLATOR_CHARS,
        cadence_hours=DAILY_CADENCE_HOURS,
    ),
    Stage(
        id="page_translation",
        label="Page translation",
        task_kinds=(),
        queue=FlowQueue.PAGE_TRANSLATION,
        run_stage=DiscoveryRunStage.SNAPSHOT_TRANSLATE,
        allotment=BudgetResource.AZURE_TRANSLATOR_CHARS,
        cadence_hours=DAILY_CADENCE_HOURS,
    ),
)

EDGES: tuple[Edge, ...] = (
    Edge("seed", "render"),
    Edge("render", "extract_page"),
    Edge("render", "llm"),
    Edge("render", "capture", manual_only=True),
    Edge("llm", "capture"),
    Edge("llm", "embed"),
    Edge("llm", "card_translation"),
    Edge("llm", "page_translation"),
)

STAGE_BY_ID: dict[str, Stage] = {stage.id: stage for stage in STAGES}


def upstream_ids(stage_id: str) -> tuple[str, ...]:
    """Return the ids of the stages that feed ``stage_id``, in edge order."""
    return tuple(edge.source for edge in EDGES if edge.target == stage_id)

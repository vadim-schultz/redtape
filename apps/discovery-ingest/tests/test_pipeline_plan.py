"""The pipeline plan: the stages with ready work and their caps, from queue summaries and ledger rows (chapter 12)."""

from __future__ import annotations

from datetime import date

from discovery_ingest.operations.pipeline import (
    STAGES,
    OmittedStage,
    PlanContext,
    PlanFacts,
    build_plan,
    read_plan_facts,
    stage_by_id,
)

from cli_adapters import accepts
from pipeline_fakes import FakeMachine, row


def facts(
    ready: dict[str, int] | None = None,
    *,
    browser: float = 570.0,
    neurons: float = 8500.0,
    unconfigured: frozenset[str] = frozenset(),
) -> PlanFacts:
    """Return plan facts with ``ready`` work per stage and the given headroom of browser seconds and neurons."""
    return PlanFacts(
        ready=ready or {},
        headroom={"browser_seconds": browser, "neurons": neurons},
        actions_minutes_remaining=600.0,
        days_left=10,
        unconfigured=unconfigured,
    )


def reasons(omitted: list[OmittedStage]) -> set[tuple[str, str]]:
    """Return the ``(stage, reason)`` pairs of the omitted stages."""
    return {(item.stage, item.reason) for item in omitted}


def test_plan_omits_a_stage_with_no_ready_work() -> None:
    plan = build_plan(facts({"render": 4}))

    assert [planned.stage for planned in plan.stages] == ["render"]
    assert ("embed", "no ready work") in reasons(plan.omitted)


def test_plan_includes_a_stage_with_ready_work_and_its_cap() -> None:
    plan = build_plan(facts({"embed": 120}))

    (embed,) = plan.stages
    assert embed.stage == "embed"
    assert embed.ready == 120
    assert embed.caps == {"neurons": 3000.0}


def test_plan_grants_neurons_in_run_order_and_never_above_the_headroom() -> None:
    plan = build_plan(facts({"embed": 500, "llm": 40, "card_tail": 30}, neurons=4000.0))

    granted = {planned.stage: planned.caps["neurons"] for planned in plan.stages}
    assert granted == {"embed": 3000.0, "llm": 1000.0}
    assert sum(granted.values()) <= 4000.0
    assert ("card_tail", "allotment short") in reasons(plan.omitted)


def test_plan_omits_a_stage_whose_allotment_is_below_its_floor() -> None:
    plan = build_plan(facts({"embed": 9}, neurons=50.0))

    assert plan.stages == []
    assert ("embed", "allotment short") in reasons(plan.omitted)


def test_plan_leaves_out_a_stage_that_is_not_configured() -> None:
    plan = build_plan(facts({"llm": 50}, unconfigured=frozenset({"llm"})))

    assert plan.stages == []
    assert ("llm", "not configured") in reasons(plan.omitted)


def test_plan_gives_browser_seconds_to_render_before_capture() -> None:
    plan = build_plan(facts({"render": 5, "capture": 5}, browser=600.0))

    caps = {planned.stage: planned.caps["browser_seconds"] for planned in plan.stages}
    assert caps == {"render": 570.0, "capture": 30.0}


def test_every_planned_stage_builds_arguments_the_cli_accepts() -> None:
    plan = build_plan(facts({spec.id: 5 for spec in STAGES}, browser=1000.0))

    assert len(plan.stages) == len(STAGES)
    for planned in plan.stages:
        argv = stage_by_id(planned.stage).argv(planned.caps, 600.0)
        assert accepts(argv), argv


def test_the_reader_reads_each_summary_and_the_ledger_once_and_folds_the_sweep_into_capture() -> None:
    machine = FakeMachine(
        ready_by_kinds={"capture_screenshot": 2, "render_page": 7},
        embeddings=11,
        cards={"tr": 4, "uk": 3},
        pages=5,
        budget_rows=[row("browser_seconds", 400.0), row("neurons", 3000.0), row("actions_minutes", 90.0)],
        missing=3,
    )
    context = PlanContext(
        today=date(2026, 11, 20),
        embedding_model="@cf/baai/bge-m3",
        query_embed_reserve=1000.0,
        tail_locales=("tr",),
        llm_model="@cf/qwen/qwen3-30b-a3b-fp8",
    )

    read = read_plan_facts(machine, context)

    assert read.ready["capture"] == 5
    assert read.ready["render"] == 7
    assert read.ready["embed"] == 11
    assert read.ready["card_translation"] == 7
    assert read.ready["card_tail"] == 4
    assert read.ready["page_translation"] == 5
    assert read.headroom == {"browser_seconds": 400.0, "neurons": 2000.0}
    assert read.actions_minutes_remaining == 90.0
    assert read.days_left == 11
    assert read.unconfigured == frozenset()
    assert machine.calls["budget"] == 1
    assert machine.calls["embeddings"] == 1
    assert machine.calls["translations"] == 1
    assert machine.calls["snapshots"] == 1
    assert machine.calls["missing_screenshot"] == 1
    assert all(count == 1 for count in machine.calls.values())


def test_the_reader_marks_the_model_and_the_tail_unconfigured_when_they_are_not_set() -> None:
    context = PlanContext(
        today=date(2026, 11, 30),
        embedding_model="@cf/baai/bge-m3",
        query_embed_reserve=1000.0,
        tail_locales=(),
        llm_model="",
    )

    read = read_plan_facts(FakeMachine(budget_rows=[row("actions_minutes", 10.0)]), context)

    assert read.unconfigured == frozenset({"llm", "card_tail"})
    assert read.days_left == 1

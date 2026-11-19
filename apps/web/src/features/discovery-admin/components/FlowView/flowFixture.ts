import type {
  DiscoveryFlowResponse,
  FlowLastRun,
  FlowStage,
} from "../../types";

/** A stage with the values a quiet, healthy stage reports; tests override only what they assert. */
export function flowStage(
  id: string,
  label: string,
  overrides: Partial<FlowStage> = {},
): FlowStage {
  return {
    id,
    label,
    state: "flowing",
    ready: 0,
    failed_24h: 0,
    last_run: null,
    ...overrides,
  };
}

/** A finished run that stopped for `stopReason`. */
export function finishedRun(stopReason: string | null): FlowLastRun {
  return {
    status: "succeeded",
    stop_reason: stopReason,
    started_at: "2026-11-19T10:00:00Z",
    finished_at: "2026-11-19T10:05:00Z",
  };
}

/** The eight stages of the chapter 13 topology, in topology order, with one stage of each kind of trouble. */
export function flowFixture(): DiscoveryFlowResponse {
  return {
    stages: [
      flowStage("seed", "Seed", {
        state: "starved",
        last_run: finishedRun("queue_empty"),
      }),
      flowStage("render", "Render", {
        state: "budget_stopped",
        ready: 12,
        failed_24h: 3,
        last_run: finishedRun("time_budget"),
      }),
      flowStage("extract_page", "Extract (rules)", { state: "dead" }),
      flowStage("llm", "Extract (LLM)", {
        state: "throttled",
        ready: 40,
        last_run: finishedRun("rate_limited"),
      }),
      flowStage("capture", "Screenshot", { state: "idle" }),
      flowStage("embed", "Embed", { state: "overdue" }),
      flowStage("card_translation", "Card translation", {
        state: "backlogged",
        ready: 4200,
      }),
      flowStage("page_translation", "Page translation", { state: "idle" }),
    ],
    edges: [
      { from: "seed", to: "render", tasks_created_24h: 5, manual_only: false },
      {
        from: "render",
        to: "extract_page",
        tasks_created_24h: 0,
        manual_only: false,
      },
      { from: "render", to: "llm", tasks_created_24h: 9, manual_only: false },
      {
        from: "render",
        to: "capture",
        tasks_created_24h: 0,
        manual_only: true,
      },
      { from: "llm", to: "capture", tasks_created_24h: 0, manual_only: false },
      { from: "llm", to: "embed", tasks_created_24h: 0, manual_only: false },
      {
        from: "llm",
        to: "card_translation",
        tasks_created_24h: 0,
        manual_only: false,
      },
      {
        from: "llm",
        to: "page_translation",
        tasks_created_24h: 0,
        manual_only: false,
      },
    ],
    allotments: [
      {
        resource: "browser_seconds",
        used: 244,
        cap: 570,
        spent_by_stage: { worker_drain: 244 },
      },
      {
        resource: "neurons",
        used: 930,
        cap: 9500,
        spent_by_stage: { worker_drain: 600, embed: 330 },
      },
      {
        resource: "azure_translator_chars",
        used: 26832,
        cap: 1900000,
        spent_by_stage: { snapshot_translate: 26832 },
      },
    ],
    unused_headroom: [{ resource: "neurons", stage: "card_translation" }],
  };
}

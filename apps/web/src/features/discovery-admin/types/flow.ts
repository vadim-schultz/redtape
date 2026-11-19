import type { FlowResource, FlowRunStatus, FlowStageState } from "./values";

/** The newest run of a flow stage, as the flow route reports it. */
export type FlowLastRun = {
  status: FlowRunStatus;
  stop_reason: string | null;
  started_at: string;
  finished_at: string | null;
};

/** One stage of the flow: its state, its ready work, its failures in 24 h and its last run. */
export type FlowStage = {
  id: string;
  label: string;
  state: FlowStageState;
  ready: number;
  failed_24h: number;
  last_run: FlowLastRun | null;
};

/** How a stage feeds the next. `manual_only` marks a feed that only an operator command makes. */
export type FlowEdge = {
  from: string;
  to: string;
  tasks_created_24h: number;
  manual_only: boolean;
};

/** One free-tier allotment, with its spend in the last 24 h keyed by run stage. */
export type FlowAllotment = {
  resource: FlowResource;
  used: number;
  cap: number;
  spent_by_stage: Record<string, number>;
};

/** A stage with ready work that draws on an allotment with headroom left. */
export type FlowHeadroom = {
  resource: FlowResource;
  stage: string;
};

/** The admin pipeline flow (`GET /api/v1/discovery/admin/flow`). */
export type DiscoveryFlowResponse = {
  stages: FlowStage[];
  edges: FlowEdge[];
  allotments: FlowAllotment[];
  unused_headroom: FlowHeadroom[];
};

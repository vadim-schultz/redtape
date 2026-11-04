import type { DiscoverySource } from "./values";

export type DiscoveryTaskCounts = {
  total: number;
  pending: number;
  claimed: number;
  completed: number;
  failed: number;
};

export type DiscoveryCandidateCounts = {
  total: number;
  staged: number;
  emitted: number;
  mentions: number;
};

export type DiscoveryRun = {
  id: string;
  kind: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  claimed_count: number;
  completed_count: number;
  failed_count: number;
  skipped_count: number;
  remaining_count: number | null;
  stop_reason: string | null;
  error_detail: string | null;
};

/** Artifact count and stored bytes of one kind. */
export type DiscoveryArtifactTotals = { count: number; bytes: number };

/** Stored artifacts per kind against the storage cap the API reports. */
export type DiscoveryArtifactCoverage = {
  /** Keyed by artifact kind; a kind this client does not know yet still counts. */
  by_kind: Record<string, DiscoveryArtifactTotals>;
  total_bytes: number;
  bytes_cap: number;
};

/** Completed `llm_extract` tasks by what the model run produced. */
export type DiscoveryLlmOutcomes = {
  extracted: number;
  no_documents: number;
  login_wall: number;
  no_content: number;
};

export type DiscoveryCoverageResponse = {
  by_source: Partial<Record<DiscoverySource, number>>;
  tasks_pending: number;
  tasks_failed: number;
  emit_ready_count: number;
  task_counts: DiscoveryTaskCounts;
  /** Keyed by task kind; a kind this client does not know yet still renders. */
  task_counts_by_kind: Record<string, DiscoveryTaskCounts>;
  candidates: DiscoveryCandidateCounts;
  llm_outcomes: DiscoveryLlmOutcomes;
  artifacts: DiscoveryArtifactCoverage;
  fetch_attempts_total: number;
  stale_claims: number;
  stale_runs: number;
  failures_by_source: Partial<Record<DiscoverySource, number>>;
  last_successful_run: DiscoveryRun | null;
};

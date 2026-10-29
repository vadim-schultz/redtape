import type { DiscoveryCoverageResponse, DiscoveryRun } from "../../types";

/** A populated coverage response shared by the summary, table and page tests. */
export const baseCoverage: DiscoveryCoverageResponse = {
  by_source: { govdata: 2, pvog: 1 },
  tasks_pending: 3,
  tasks_failed: 1,
  emit_ready_count: 4,
  task_counts: { total: 9, pending: 3, claimed: 2, completed: 3, failed: 1 },
  task_counts_by_kind: {
    fetch_url: { total: 6, pending: 2, claimed: 1, completed: 3, failed: 0 },
    harvest_payload: {
      total: 3,
      pending: 1,
      claimed: 1,
      completed: 0,
      failed: 1,
    },
  },
  candidates: { total: 5, staged: 3, emitted: 2, mentions: 9 },
  llm_outcomes: { extracted: 7, no_documents: 0, login_wall: 0, no_content: 1 },
  artifacts: {
    by_kind: {
      html_snapshot: { count: 3, bytes: 3 * 1024 ** 3 - 1024 },
      screenshot: { count: 2, bytes: 1024 },
    },
    total_bytes: 3 * 1024 ** 3,
    bytes_cap: 8 * 1024 ** 3,
  },
  fetch_attempts_total: 12,
  stale_claims: 2,
  stale_runs: 1,
  failures_by_source: { fim: 1 },
  last_successful_run: null,
};

/** A coverage response with nothing recorded yet. */
export const emptyCoverage: DiscoveryCoverageResponse = {
  ...baseCoverage,
  by_source: {},
  tasks_pending: 0,
  tasks_failed: 0,
  emit_ready_count: 0,
  task_counts: { total: 0, pending: 0, claimed: 0, completed: 0, failed: 0 },
  task_counts_by_kind: {},
  candidates: { total: 0, staged: 0, emitted: 0, mentions: 0 },
  llm_outcomes: { extracted: 0, no_documents: 0, login_wall: 0, no_content: 0 },
  artifacts: { by_kind: {}, total_bytes: 0, bytes_cap: 8 * 1024 ** 3 },
  fetch_attempts_total: 0,
  stale_claims: 0,
  stale_runs: 0,
  failures_by_source: {},
};

/** A finished worker run for the last-run table. */
export const finishedRun: DiscoveryRun = {
  id: "run-1",
  kind: "worker_drain",
  status: "succeeded",
  started_at: "2026-10-23T10:00:00Z",
  finished_at: "2026-10-23T10:05:00Z",
  claimed_count: 5,
  completed_count: 4,
  failed_count: 1,
  skipped_count: 0,
  remaining_count: null,
  stop_reason: "batch_limit",
  error_detail: null,
};

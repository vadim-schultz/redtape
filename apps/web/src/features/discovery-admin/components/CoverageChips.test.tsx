import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import type { DiscoveryCoverageResponse } from "../types";
import CoverageChips from "./CoverageChips";

const baseCoverage: DiscoveryCoverageResponse = {
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
  artifacts: { by_kind: {}, total_bytes: 0, bytes_cap: 8_589_934_592 },
  fetch_attempts_total: 12,
  stale_claims: 2,
  stale_runs: 1,
  failures_by_source: { fim: 1 },
  last_successful_run: null,
};

it("CoverageChips · renders source counts from API", () => {
  renderWithProviders(<CoverageChips coverage={baseCoverage} />);

  expect(screen.getByText("govdata: 2")).toBeInTheDocument();
  expect(screen.getByText("pvog: 1")).toBeInTheDocument();
  expect(screen.getByText("Pending tasks: 3")).toBeInTheDocument();
  expect(screen.getByText("Failed tasks: 1")).toBeInTheDocument();
  expect(screen.getByText("Emit-ready: 4")).toBeInTheDocument();
});

it("CoverageChips · renders queue and run metrics", () => {
  renderWithProviders(
    <CoverageChips
      coverage={{
        ...baseCoverage,
        last_successful_run: {
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
        },
      }}
    />,
  );

  expect(screen.getByText("Total tasks: 9")).toBeInTheDocument();
  expect(screen.getByText("Claimed tasks: 2")).toBeInTheDocument();
  expect(screen.getByText("Completed tasks: 3")).toBeInTheDocument();
  expect(screen.getByText("Fetch attempts: 12")).toBeInTheDocument();
  expect(screen.getByText("Stale leases: 2")).toBeInTheDocument();
  expect(screen.getByText("Stale runs: 1")).toBeInTheDocument();
  expect(screen.getByText("Failed tasks by source")).toBeInTheDocument();
  expect(screen.getByText(/Last successful run:/)).toBeInTheDocument();
  expect(
    screen.getByText(
      "Claimed 5, completed 4, failed 1, skipped 0; stopped: batch_limit",
    ),
  ).toBeInTheDocument();
});

it("CoverageChips · states that no successful run exists without success wording", () => {
  renderWithProviders(<CoverageChips coverage={baseCoverage} />);

  expect(
    screen.getByText("No successful run recorded yet."),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Last successful run:/)).not.toBeInTheDocument();
});

it("CoverageChips · renders per-kind task chips and candidate totals", () => {
  renderWithProviders(<CoverageChips coverage={baseCoverage} />);

  expect(
    screen.getByText("harvest_payload: 1 pending, 1 claimed, 0 done, 1 failed"),
  ).toBeInTheDocument();
  expect(
    screen.getByText("fetch_url: 2 pending, 1 claimed, 3 done, 0 failed"),
  ).toBeInTheDocument();
  expect(screen.getByText("Candidates: 5")).toBeInTheDocument();
  expect(screen.getByText("Staged candidates: 3")).toBeInTheDocument();
  expect(screen.getByText("Emitted candidates: 2")).toBeInTheDocument();
  expect(screen.getByText("Candidate mentions: 9")).toBeInTheDocument();
});

it("CoverageChips · renders no kind chip when the API reports no kinds", () => {
  renderWithProviders(
    <CoverageChips coverage={{ ...baseCoverage, task_counts_by_kind: {} }} />,
  );

  expect(screen.queryByText(/ pending, .* claimed, /)).not.toBeInTheDocument();
  expect(screen.getByText("Candidates: 5")).toBeInTheDocument();
});

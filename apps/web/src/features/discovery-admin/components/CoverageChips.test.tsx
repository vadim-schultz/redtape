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

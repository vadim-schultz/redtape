import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import DiscoveryCoveragePage from "./DiscoveryCoveragePage";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubCoverageFetch(
  handler: () => Response,
  budgets: () => Response = () => new Response("", { status: 503 }),
) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/api/v1/me")) {
        return new Response(
          JSON.stringify({
            id: "user-1",
            email: session.email,
            display_name: null,
            role: "user",
          }),
        );
      }
      if (url.pathname.endsWith("/api/v1/discovery/admin/coverage")) {
        return handler();
      }
      if (url.pathname.endsWith("/api/v1/discovery/admin/budgets")) {
        return budgets();
      }
      return new Response("", { status: 503 });
    }),
  );
}

it("Coverage page · shows an explicit empty run state for an empty queue", async () => {
  stubCoverageFetch(
    () =>
      new Response(
        JSON.stringify({
          by_source: {},
          tasks_pending: 0,
          tasks_failed: 0,
          emit_ready_count: 0,
          task_counts: {
            total: 0,
            pending: 0,
            claimed: 0,
            completed: 0,
            failed: 0,
          },
          task_counts_by_kind: {
            harvest_payload: {
              total: 4,
              pending: 4,
              claimed: 0,
              completed: 0,
              failed: 0,
            },
          },
          candidates: { total: 0, staged: 0, emitted: 0, mentions: 0 },
          llm_outcomes: {
            extracted: 0,
            no_documents: 0,
            login_wall: 0,
            no_content: 0,
          },
          artifacts: { by_kind: {}, total_bytes: 0, bytes_cap: 8589934592 },
          fetch_attempts_total: 0,
          stale_claims: 0,
          stale_runs: 0,
          failures_by_source: {},
          last_successful_run: null,
        }),
      ),
  );

  renderWithProviders(<DiscoveryCoveragePage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByText("No successful run recorded yet."),
  ).toBeInTheDocument();
  expect(screen.getByText("No failed tasks.")).toBeInTheDocument();
  expect(
    screen.getByText("harvest_payload: 4 pending, 0 claimed, 0 done, 0 failed"),
  ).toBeInTheDocument();
  expect(screen.getByText("Candidates: 0")).toBeInTheDocument();
});

it("Coverage page · shows unavailable state instead of zero-success language", async () => {
  stubCoverageFetch(() => new Response("", { status: 500 }));

  renderWithProviders(<DiscoveryCoveragePage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument(),
  );
  expect(
    screen.queryByText("No successful run recorded yet."),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Total tasks: 0")).not.toBeInTheDocument();
});

function emptyCoverage(): Response {
  return new Response(
    JSON.stringify({
      by_source: {},
      tasks_pending: 0,
      tasks_failed: 0,
      emit_ready_count: 0,
      task_counts: {
        total: 0,
        pending: 0,
        claimed: 0,
        completed: 0,
        failed: 0,
      },
      task_counts_by_kind: {},
      candidates: { total: 0, staged: 0, emitted: 0, mentions: 0 },
      llm_outcomes: {
        extracted: 4,
        no_documents: 1,
        login_wall: 0,
        no_content: 2,
      },
      artifacts: { by_kind: {}, total_bytes: 0, bytes_cap: 8589934592 },
      fetch_attempts_total: 0,
      stale_claims: 0,
      stale_runs: 0,
      failures_by_source: {},
      last_successful_run: null,
    }),
  );
}

it("Coverage page · shows the budget meters from the admin budgets route", async () => {
  stubCoverageFetch(
    emptyCoverage,
    () =>
      new Response(
        JSON.stringify({
          items: [
            {
              resource: "actions_minutes",
              period: "2026-10",
              cap: 400,
              used: 30,
              remaining: 370,
              exhausted: false,
            },
          ],
          stored_bytes: 0,
          stored_bytes_cap: 8589934592,
        }),
      ),
  );

  renderWithProviders(<DiscoveryCoveragePage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByText("Actions minutes · 2026-10"),
  ).toBeInTheDocument();
  expect(screen.getByText("30 of 400 used, 370 left")).toBeInTheDocument();
});

it("Coverage page · keeps the coverage chips when only the budgets fail to load", async () => {
  stubCoverageFetch(emptyCoverage);

  renderWithProviders(<DiscoveryCoveragePage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByText("Could not load the budgets."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("No successful run recorded yet."),
  ).toBeInTheDocument();
});

it("Coverage page · shows the llm_extract outcomes and the neuron meter once, not among the other budgets", async () => {
  stubCoverageFetch(
    emptyCoverage,
    () =>
      new Response(
        JSON.stringify({
          items: [
            {
              resource: "neurons",
              period: "2026-10-29",
              cap: 9500,
              used: 2500,
              remaining: 7000,
              exhausted: false,
            },
          ],
          stored_bytes: 0,
          stored_bytes_cap: 8589934592,
        }),
      ),
  );

  renderWithProviders(<DiscoveryCoveragePage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(await screen.findByText("Extracted: 4")).toBeInTheDocument();
  expect(screen.getByText("No content: 2")).toBeInTheDocument();
  expect(
    await screen.findByText("2,500 of 9,500 used, 7,000 left"),
  ).toBeInTheDocument();
  expect(screen.getAllByText(/AI neurons/)).toHaveLength(1);
});

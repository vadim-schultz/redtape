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

function stubCoverageFetch(handler: () => Response) {
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

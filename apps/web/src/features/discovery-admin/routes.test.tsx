import { screen, waitFor } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import { createFakeAuthGateway } from "../auth/services/fakeAuthGateway";
import type { AuthSession } from "../auth/services/authGateway";
import DiscoveryAdminRoutes from "./routes";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const coverageResponse = {
  by_source: { govdata: 3 },
  tasks_pending: 2,
  tasks_failed: 1,
  emit_ready_count: 4,
  task_counts: { total: 3, pending: 2, claimed: 0, completed: 0, failed: 1 },
  task_counts_by_kind: {},
  candidates: { total: 0, staged: 0, emitted: 0, mentions: 0 },
  fetch_attempts_total: 0,
  stale_claims: 0,
  stale_runs: 0,
  failures_by_source: {},
  last_successful_run: null,
};

function Mounted() {
  return (
    <Routes>
      <Route path="/admin/discovery/*" element={<DiscoveryAdminRoutes />} />
    </Routes>
  );
}

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubDiscoveryFetch(coverageStatus = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const pathname = new URL(String(input)).pathname;

      if (pathname.endsWith("/api/v1/me")) {
        return new Response(
          JSON.stringify({
            id: "user-1",
            email: session.email,
            display_name: null,
            role: "user",
          }),
        );
      }

      if (pathname.endsWith("/api/v1/discovery/admin/tasks")) {
        return new Response(
          JSON.stringify({ items: [], total: 0, offset: 0, limit: 1 }),
        );
      }

      if (pathname.endsWith("/api/v1/discovery/admin/coverage")) {
        if (coverageStatus !== 200)
          return new Response("", { status: coverageStatus });
        return new Response(JSON.stringify(coverageResponse));
      }

      return new Response("", { status: 503 });
    }),
  );
}

it("DiscoveryAdminRoutes · renders the coverage page at /admin/discovery/coverage", async () => {
  stubDiscoveryFetch();

  renderWithProviders(<Mounted />, {
    initialEntries: ["/admin/discovery/coverage"],
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(await screen.findByText("govdata: 3")).toBeInTheDocument();
});

it("DiscoveryAdminRoutes · renders a fallback for an unknown discovery path", async () => {
  stubDiscoveryFetch();

  renderWithProviders(<Mounted />, {
    initialEntries: ["/admin/discovery/unknown"],
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
});

it("DiscoveryCoveragePage · shows an error and retry action when coverage fails", async () => {
  stubDiscoveryFetch(500);

  renderWithProviders(<Mounted />, {
    initialEntries: ["/admin/discovery/coverage"],
    authGateway: createFakeAuthGateway({ session }),
  });

  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument(),
  );
});

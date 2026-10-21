import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import { createFakeAuthGateway } from "../auth/services/fakeAuthGateway";
import type { AuthSession } from "../auth/services/authGateway";
import DiscoveryAdminRoutes from "./DiscoveryAdminRoutes";

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
};

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

  renderWithProviders(<DiscoveryAdminRoutes />, {
    initialEntries: ["/admin/discovery/coverage"],
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(await screen.findByText("govdata: 3")).toBeInTheDocument();
});

it("DiscoveryAdminRoutes · renders a fallback for an unknown discovery path", async () => {
  stubDiscoveryFetch();

  renderWithProviders(<DiscoveryAdminRoutes />, {
    initialEntries: ["/admin/discovery/unknown"],
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
});

it("DiscoveryCoveragePage · shows an error and retry action when coverage fails", async () => {
  stubDiscoveryFetch(500);

  renderWithProviders(<DiscoveryAdminRoutes />, {
    initialEntries: ["/admin/discovery/coverage"],
    authGateway: createFakeAuthGateway({ session }),
  });

  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument(),
  );
});

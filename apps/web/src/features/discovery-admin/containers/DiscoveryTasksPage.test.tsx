import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import DiscoveryTasksPage from "./DiscoveryTasksPage";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const adminTasksUrl = "/api/v1/discovery/admin/tasks";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubTasksFetch(handler: (url: URL) => Response | Promise<Response>) {
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
      if (url.pathname.endsWith(adminTasksUrl)) {
        return handler(url);
      }
      return new Response("", { status: 503 });
    }),
  );
}

it("DiscoveryTasksPage · renders rows from mocked admin tasks API", async () => {
  stubTasksFetch(
    () =>
      new Response(
        JSON.stringify({
          items: [
            {
              id: "task-1",
              catalogue_service_id: "cat-1",
              source: "govdata",
              kind: "fetch_url",
              target_url: "https://example.gov/service",
              status: "pending",
              priority: 100,
              lease_expires_at: null,
              created_at: "2026-01-01T12:00:00Z",
              updated_at: "2026-01-01T12:00:00Z",
            },
          ],
          total: 1,
          offset: 0,
          limit: 20,
        }),
      ),
  );

  renderWithProviders(<DiscoveryTasksPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  const table = await screen.findByRole("table");
  expect(table).toHaveTextContent("https://example.gov/service");
  expect(table).toHaveTextContent("pending");
  expect(table).toHaveTextContent("govdata");
});

it("DiscoveryTasksPage · shows error state when query fails", async () => {
  stubTasksFetch(() => new Response("", { status: 500 }));

  renderWithProviders(<DiscoveryTasksPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument(),
  );
});

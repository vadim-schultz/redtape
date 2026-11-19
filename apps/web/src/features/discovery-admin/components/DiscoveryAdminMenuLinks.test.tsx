import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import type { AuthSession } from "../../auth/services/authGateway";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import DiscoveryAdminMenuLinks from "./DiscoveryAdminMenuLinks";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

/** Stub the admin probe (the task list) with `status`, and the user call with a plain user. */
function stubProbe(status: number) {
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
        return status === 200
          ? new Response(
              JSON.stringify({ items: [], total: 0, offset: 0, limit: 1 }),
            )
          : new Response("", { status });
      }
      return new Response("", { status: 503 });
    }),
  );
}

it("the flow link is an admin link that sits after Coverage", async () => {
  stubProbe(200);

  renderWithProviders(<DiscoveryAdminMenuLinks />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  const flow = await screen.findByRole("link", { name: "Flow" });
  expect(flow).toHaveAttribute("href", "/admin/discovery/flow");
  const hrefs = screen
    .getAllByRole("link")
    .map((link) => link.getAttribute("href"));
  expect(hrefs).toEqual([
    "/admin/discovery/catalogue",
    "/admin/discovery/coverage",
    "/admin/discovery/flow",
    "/admin/discovery/tasks",
    "/admin/discovery/documents",
  ]);
});

it("a non-admin does not see the flow link", async () => {
  stubProbe(403);

  renderWithProviders(<DiscoveryAdminMenuLinks />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  await waitFor(() => expect(screen.queryAllByRole("link")).toHaveLength(0));
  expect(screen.queryByRole("link", { name: "Flow" })).not.toBeInTheDocument();
});

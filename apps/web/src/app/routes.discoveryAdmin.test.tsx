import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import AppLayout from "../components/layout/AppLayout";
import { createFakeAuthGateway } from "../features/auth/services/fakeAuthGateway";
import type { AuthSession } from "../features/auth/services/authGateway";
import { renderWithProviders } from "../test/renderWithProviders";
import App from "./App";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const pathname = new URL(String(input)).pathname;
      if (pathname.endsWith("/api/v1/me"))
        return new Response(
          JSON.stringify({
            id: "user-1",
            email: session.email,
            display_name: null,
            role: "user",
          }),
        );
      if (pathname.endsWith("/discovery/admin/tasks"))
        return new Response(
          JSON.stringify({ items: [], total: 0, offset: 0, limit: 1 }),
        );
      if (pathname.endsWith("/discovery/admin/coverage"))
        return new Response(
          JSON.stringify({
            by_source: { govdata: 3 },
            tasks_pending: 2,
            tasks_failed: 1,
            emit_ready_count: 4,
          }),
        );
      return new Response("", { status: 503 });
    }),
  );
}

function renderAppAt(path: string) {
  stubFetch();
  return renderWithProviders(
    <AppLayout>
      <App />
    </AppLayout>,
    {
      initialEntries: [path],
      authGateway: createFakeAuthGateway({ session }),
    },
  );
}

it("app · renders the discovery coverage page at /admin/discovery/coverage", async () => {
  renderAppAt("/admin/discovery/coverage");

  expect(await screen.findByText("govdata: 3")).toBeInTheDocument();
});

it("app · renders not-found for an unknown discovery path", async () => {
  renderAppAt("/admin/discovery/unknown");

  expect(
    await screen.findByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
});

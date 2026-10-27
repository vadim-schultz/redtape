import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import AppLayout from "../components/layout/AppLayout";
import { createFakeAuthGateway } from "../features/auth/services/fakeAuthGateway";
import type { AuthSession } from "../features/auth/services/authGateway";
import { renderWithProviders } from "../test/renderWithProviders";
import App from "./App";

vi.mock("./retryPolicy", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./retryPolicy")>()),
  retryDelay: () => 0,
}));

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubFetch(probeStatus = 200) {
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
        return probeStatus === 200
          ? new Response(
              JSON.stringify({ items: [], total: 0, offset: 0, limit: 1 }),
            )
          : new Response("", { status: probeStatus });
      if (pathname.endsWith("/discovery/admin/coverage"))
        return new Response(
          JSON.stringify({
            by_source: { govdata: 3 },
            tasks_pending: 2,
            tasks_failed: 1,
            emit_ready_count: 4,
            task_counts: {
              total: 3,
              pending: 2,
              claimed: 0,
              completed: 0,
              failed: 1,
            },
            task_counts_by_kind: {},
            candidates: { total: 0, staged: 0, emitted: 0, mentions: 0 },
            artifacts: { by_kind: {}, total_bytes: 0, bytes_cap: 8589934592 },
            fetch_attempts_total: 0,
            stale_claims: 0,
            stale_runs: 0,
            failures_by_source: {},
            last_successful_run: null,
          }),
        );
      return new Response("", { status: 503 });
    }),
  );
}

function renderAppAt(
  path: string,
  { probeStatus = 200, signedIn = true } = {},
) {
  stubFetch(probeStatus);
  return renderWithProviders(
    <AppLayout>
      <App />
    </AppLayout>,
    {
      initialEntries: [path],
      authGateway: createFakeAuthGateway({
        session: signedIn ? session : null,
      }),
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

it("app · menu Coverage link opens the coverage page", async () => {
  const { user } = renderAppAt("/documents");

  await user.click(await screen.findByRole("button", { name: "Menu" }));
  await user.click(await screen.findByRole("link", { name: "Coverage" }));

  expect(await screen.findByText("govdata: 3")).toBeInTheDocument();
});

it("app · anonymous visitor at /admin/discovery/catalogue lands on login", async () => {
  renderAppAt("/admin/discovery/catalogue", { signedIn: false });

  expect(
    await screen.findByRole("button", { name: /send|sign in|log in/i }),
  ).toBeInTheDocument();
});

it.each([
  { status: 403, text: "Access denied", name: "the forbidden view" },
  {
    status: 503,
    text: "Discovery admin is disabled",
    name: "the disabled message with retry",
  },
])("app · probe $status shows $name", async ({ status, text }) => {
  renderAppAt("/admin/discovery/catalogue", { probeStatus: status });

  expect(await screen.findByText(text)).toBeInTheDocument();
});

it("app · probe 503 offers the retry action", async () => {
  renderAppAt("/admin/discovery/catalogue", { probeStatus: 503 });

  expect(
    await screen.findByRole("button", { name: "Try again" }),
  ).toBeInTheDocument();
});

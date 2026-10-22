import {
  Route,
  Routes,
  useLocation,
  type InitialEntry,
} from "react-router-dom";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import { createFakeAuthGateway } from "../auth/services/fakeAuthGateway";
import type { AuthSession } from "../auth/services/authGateway";
import RequireDiscoveryAdmin from "./RequireDiscoveryAdmin";

vi.mock("../../app/retryPolicy", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../app/retryPolicy")>()),
  retryDelay: () => 0,
}));

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const adminTasksUrl = "/api/v1/discovery/admin/tasks";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubFetch(adminStatus: number) {
  const fetchMock = vi.fn(async (input?: unknown) => {
    const url = String(input);
    if (url.includes("/api/v1/me")) {
      return new Response(
        JSON.stringify({
          id: "user-1",
          email: session.email,
          display_name: null,
          role: "user",
        }),
      );
    }
    if (url.includes(adminTasksUrl)) {
      if (adminStatus === 200) {
        return new Response(
          JSON.stringify({ items: [], total: 0, offset: 0, limit: 1 }),
        );
      }
      return new Response("", { status: adminStatus });
    }
    return new Response("", { status: 503 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function LoginProbe() {
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from
    ?.pathname;
  return <div>login-page from:{from ?? "none"}</div>;
}

function renderGuard(
  authGateway: ReturnType<typeof createFakeAuthGateway>,
  adminStatus: number,
  initialEntries: InitialEntry[] = ["/protected"],
) {
  stubFetch(adminStatus);
  return renderWithProviders(
    <Routes>
      <Route
        path="/protected"
        element={
          <RequireDiscoveryAdmin>
            <div>discovery-admin-content</div>
          </RequireDiscoveryAdmin>
        }
      />
      <Route path="/login" element={<LoginProbe />} />
    </Routes>,
    { initialEntries, authGateway },
  );
}

it("RequireDiscoveryAdmin · renders children when admin API returns 200", async () => {
  renderGuard(createFakeAuthGateway({ session }), 200);

  expect(
    await screen.findByText("discovery-admin-content"),
  ).toBeInTheDocument();
});

it("RequireDiscoveryAdmin · renders forbidden when admin API returns 403", async () => {
  renderGuard(createFakeAuthGateway({ session }), 403);

  expect(await screen.findByText("Access denied")).toBeInTheDocument();
});

it("RequireDiscoveryAdmin · redirects or shows login when unauthenticated", async () => {
  stubFetch(200);
  renderWithProviders(
    <Routes>
      <Route
        path="/protected"
        element={
          <RequireDiscoveryAdmin>
            <div>discovery-admin-content</div>
          </RequireDiscoveryAdmin>
        }
      />
      <Route path="/login" element={<LoginProbe />} />
    </Routes>,
    {
      initialEntries: ["/protected"],
      authGateway: createFakeAuthGateway({ session: null }),
    },
  );

  expect(
    await screen.findByText("login-page from:/protected"),
  ).toBeInTheDocument();
});

it("RequireDiscoveryAdmin · redirects to login when admin API returns 401", async () => {
  renderGuard(createFakeAuthGateway({ session }), 401);

  expect(
    await screen.findByText("login-page from:/protected"),
  ).toBeInTheDocument();
});

it("RequireDiscoveryAdmin · renders visible feedback while the admin probe is loading", async () => {
  stubFetch(200);
  renderGuard(createFakeAuthGateway({ session }), 200);

  expect(
    screen.getByRole("status", { name: "Loading..." }),
  ).toBeInTheDocument();
  expect(screen.queryByText("discovery-admin-content")).not.toBeInTheDocument();
  await waitFor(() =>
    expect(screen.getByText("discovery-admin-content")).toBeInTheDocument(),
  );
});

it("RequireDiscoveryAdmin · renders an auth configuration message when Supabase is unconfigured", async () => {
  renderGuard(createFakeAuthGateway({ configured: false }), 200);

  expect(
    await screen.findByRole("heading", {
      name: "Authentication is not configured",
    }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/configure Supabase before trying again/i),
  ).toBeInTheDocument();
});

it("RequireDiscoveryAdmin · explains discovery is disabled for a 503 probe", async () => {
  const { user } = renderGuard(createFakeAuthGateway({ session }), 503);
  const fetchMock = vi.mocked(fetch);

  expect(
    await screen.findByRole("heading", {
      name: "Discovery admin is disabled",
    }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/not configured on this deployment/i),
  ).toBeInTheDocument();

  const probeCalls = () =>
    fetchMock.mock.calls.filter(([input]) =>
      String(input).includes(adminTasksUrl),
    ).length;
  const callsBeforeRetry = probeCalls();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  await waitFor(() => expect(probeCalls()).toBeGreaterThan(callsBeforeRetry));
});

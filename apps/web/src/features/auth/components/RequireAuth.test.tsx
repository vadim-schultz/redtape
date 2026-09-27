import {
  Route,
  Routes,
  useLocation,
  type InitialEntry,
} from "react-router-dom";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../services/fakeAuthGateway";
import type { AuthSession } from "../services/authGateway";
import RequireAuth from "./RequireAuth";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "ada@example.com",
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubFetch(role?: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const url = String(input);
      if (url.includes("/api/v1/me") && role) {
        return new Response(
          JSON.stringify({
            id: "user-1",
            email: session.email,
            display_name: null,
            role,
          }),
        );
      }
      return new Response("", { status: 503 });
    }),
  );
}

function LoginProbe() {
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from
    ?.pathname;
  return <div>login-page from:{from ?? "none"}</div>;
}

function renderGuard(
  authGateway: ReturnType<typeof createFakeAuthGateway>,
  options: {
    minRole?: "user" | "moderator";
    initialEntries?: InitialEntry[];
  } = {},
) {
  const { minRole, initialEntries = ["/protected"] } = options;

  return renderWithProviders(
    <Routes>
      <Route
        path="/protected"
        element={
          <RequireAuth minRole={minRole}>
            <div>protected-content</div>
          </RequireAuth>
        }
      />
      <Route path="/login" element={<LoginProbe />} />
    </Routes>,
    { initialEntries, authGateway },
  );
}

it("RequireAuth · renders nothing while status is loading", () => {
  stubFetch();
  renderGuard(createFakeAuthGateway({ session: null }));

  expect(screen.queryByText("protected-content")).not.toBeInTheDocument();
  expect(screen.queryByText(/login-page/)).not.toBeInTheDocument();
});

it("RequireAuth · anonymous is redirected to /login with the origin in state", async () => {
  stubFetch();
  renderGuard(createFakeAuthGateway({ session: null }));

  expect(
    await screen.findByText("login-page from:/protected"),
  ).toBeInTheDocument();
});

it("RequireAuth · authenticated user sees the children", async () => {
  stubFetch("user");
  renderGuard(createFakeAuthGateway({ session }));

  expect(await screen.findByText("protected-content")).toBeInTheDocument();
});

it("RequireAuth · user below minRole sees the forbidden view", async () => {
  stubFetch("user");
  renderGuard(createFakeAuthGateway({ session }), { minRole: "moderator" });

  expect(await screen.findByText("Access denied")).toBeInTheDocument();
});

it("RequireAuth · moderator passes a moderator route", async () => {
  stubFetch("moderator");
  renderGuard(createFakeAuthGateway({ session }), { minRole: "moderator" });

  expect(await screen.findByText("protected-content")).toBeInTheDocument();
});

it("RequireAuth · unconfigured shows the not-found view", async () => {
  stubFetch();
  renderGuard(createFakeAuthGateway({ configured: false }));

  await waitFor(() =>
    expect(screen.getByText("Page not found")).toBeInTheDocument(),
  );
});

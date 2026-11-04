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
import RequireAuth, { guardOutcome } from "./RequireAuth";

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

it("guardOutcome · loading waits", () => {
  expect(guardOutcome("loading", undefined, "user")).toBe("wait");
});

it("guardOutcome · anonymous logs in", () => {
  expect(guardOutcome("anonymous", undefined, "user")).toBe("login");
});

it("guardOutcome · unconfigured is hidden", () => {
  expect(guardOutcome("unconfigured", undefined, "user")).toBe("hidden");
});

it("guardOutcome · a moderator passes a moderator route", () => {
  expect(guardOutcome("authenticated", "moderator", "moderator")).toBe("allow");
});

it("guardOutcome · an admin passes a moderator route", () => {
  expect(guardOutcome("authenticated", "admin", "moderator")).toBe("allow");
});

it("guardOutcome · a user passes a user route", () => {
  expect(guardOutcome("authenticated", "user", "user")).toBe("allow");
});

it("guardOutcome · a user is forbidden from a moderator route", () => {
  expect(guardOutcome("authenticated", "user", "moderator")).toBe("forbidden");
});

it("guardOutcome · an unknown role string waits", () => {
  expect(guardOutcome("authenticated", "superuser", "user")).toBe("wait");
});

it("guardOutcome · authenticated without a role waits", () => {
  expect(guardOutcome("authenticated", undefined, "user")).toBe("wait");
});

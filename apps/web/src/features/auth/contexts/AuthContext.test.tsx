import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { LocaleProvider } from "../../../contexts/LocaleContext";
import { createFakeAuthGateway } from "../services/fakeAuthGateway";
import type { AuthSession } from "../services/authGateway";
import { AuthProvider, useAuth } from "./AuthContext";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "ada@example.com",
};

function Probe() {
  const { status, signOut } = useAuth();
  return (
    <div>
      <p>{status}</p>
      <button onClick={() => void signOut()}>sign out</button>
    </div>
  );
}

function renderProbe(
  gateway: ReturnType<typeof createFakeAuthGateway>,
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  }),
) {
  return {
    user: userEvent.setup(),
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <LocaleProvider>
          <AuthProvider gateway={gateway}>
            <Probe />
          </AuthProvider>
        </LocaleProvider>
      </QueryClientProvider>,
    ),
  };
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response("{}", { status: 503 })),
  );
});
afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

it("AuthProvider · status is unconfigured when the gateway is not configured", async () => {
  const gateway = createFakeAuthGateway({ configured: false });

  renderProbe(gateway);

  await waitFor(() =>
    expect(screen.getByText("unconfigured")).toBeInTheDocument(),
  );
});

it("AuthProvider · status becomes authenticated when the gateway has a session", async () => {
  const gateway = createFakeAuthGateway({ session });

  renderProbe(gateway);

  await waitFor(() =>
    expect(screen.getByText("authenticated")).toBeInTheDocument(),
  );
});

it("AuthProvider · status becomes anonymous after sign-out", async () => {
  const gateway = createFakeAuthGateway({ session });
  renderProbe(gateway);
  await waitFor(() =>
    expect(screen.getByText("authenticated")).toBeInTheDocument(),
  );

  gateway.emit(null);

  await waitFor(() =>
    expect(screen.getByText("anonymous")).toBeInTheDocument(),
  );
});

it("AuthProvider · sign-out clears cached queries", async () => {
  const gateway = createFakeAuthGateway({ session });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  queryClient.setQueryData(["unrelated"], "value");
  const { user } = renderProbe(gateway, queryClient);
  await waitFor(() =>
    expect(screen.getByText("authenticated")).toBeInTheDocument(),
  );

  await user.click(screen.getByRole("button", { name: "sign out" }));

  await waitFor(() =>
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0),
  );
});

it("AuthProvider · a failing gateway yields anonymous instead of crashing", async () => {
  const gateway = createFakeAuthGateway({ session });
  gateway.getSession = () => Promise.reject(new Error("gateway down"));

  renderProbe(gateway);

  await waitFor(() =>
    expect(screen.getByText("anonymous")).toBeInTheDocument(),
  );
});

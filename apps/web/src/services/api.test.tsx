import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { LocaleProvider } from "../contexts/LocaleContext";
import { AuthProvider, useAuth } from "../features/auth/contexts/AuthContext";
import { createFakeAuthGateway } from "../features/auth/services/fakeAuthGateway";
import { apiRequest, useApi } from "./api";

const fetchMock = vi.fn();

function requestHeaders(index: number): Headers {
  const init = fetchMock.mock.calls[index][1] as RequestInit;
  return new Headers(init.headers);
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async () => new Response("{}"));
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

it("apiRequest · adds the bearer header when an access token is given", async () => {
  await apiRequest("/api/v1/documents", {
    locale: "en",
    accessToken: "token-1",
  });

  expect(requestHeaders(0).get("Authorization")).toBe("Bearer token-1");
});

it("apiRequest · sends no Authorization header without a token", async () => {
  await apiRequest("/api/v1/documents", { locale: "en" });

  expect(requestHeaders(0).has("Authorization")).toBe(false);
});

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const gateway = createFakeAuthGateway({
    session: {
      accessToken: "token-2",
      userId: "user-1",
      email: "ada@example.com",
    },
  });
  return (
    <QueryClientProvider client={queryClient}>
      <LocaleProvider>
        <AuthProvider gateway={gateway}>{children}</AuthProvider>
      </LocaleProvider>
    </QueryClientProvider>
  );
}

it("useApi · attaches the current session token", async () => {
  const { result } = renderHook(() => ({ api: useApi(), auth: useAuth() }), {
    wrapper,
  });

  await waitFor(() => expect(result.current.auth.status).toBe("authenticated"));

  await act(async () => {
    await result.current.api.request("/api/v1/documents");
  });

  const call = fetchMock.mock.calls.find(([url]) =>
    String(url).includes("/api/v1/documents"),
  );
  expect(call).toBeDefined();
  const headers = new Headers((call as [unknown, RequestInit])[1].headers);
  expect(headers.get("Authorization")).toBe("Bearer token-2");
});

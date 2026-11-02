import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { LocaleProvider } from "../contexts/LocaleContext";
import { AuthProvider, useAuth } from "../features/auth/contexts/AuthContext";
import { createFakeAuthGateway } from "../features/auth/services/fakeAuthGateway";
import { useApi } from "./useApi";

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

function wrapperWith(configured: boolean) {
  return function Wrapper({ children }: { children: ReactNode }) {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const gateway = configured
      ? createFakeAuthGateway({
          session: {
            accessToken: "token-2",
            userId: "user-1",
            email: "ada@example.com",
          },
        })
      : createFakeAuthGateway({ configured: false });
    return (
      <QueryClientProvider client={queryClient}>
        <LocaleProvider>
          <AuthProvider gateway={gateway}>{children}</AuthProvider>
        </LocaleProvider>
      </QueryClientProvider>
    );
  };
}

it("useApi · attaches the current session token", async () => {
  const { result } = renderHook(() => ({ api: useApi(), auth: useAuth() }), {
    wrapper: wrapperWith(true),
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

it("useApi · sends no Authorization header when signed out", async () => {
  const { result } = renderHook(() => useApi(), { wrapper: wrapperWith(false) });

  await act(async () => {
    await result.current.request("/api/v1/documents");
  });

  expect(requestHeaders(0).has("Authorization")).toBe(false);
});

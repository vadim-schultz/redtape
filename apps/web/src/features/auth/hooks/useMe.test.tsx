import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { LocaleProvider } from "../../../contexts/LocaleContext";
import { useMe } from "./useMe";

const fetchMock = vi.fn();

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <LocaleProvider>{children}</LocaleProvider>
    </QueryClientProvider>
  );
}

function meCalls(): unknown[] {
  return fetchMock.mock.calls.filter(([url]) => String(url).includes("/api/v1/me"));
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        id: "user-1",
        email: "ada@example.com",
        display_name: "Ada",
        role: "user",
      }),
    ),
  );
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

it("useMe · fetches /me only when authenticated", async () => {
  const { result, rerender } = renderHook<
    ReturnType<typeof useMe>,
    { accessToken?: string; userId?: string }
  >(({ accessToken, userId }) => useMe(accessToken, userId), {
    wrapper,
    initialProps: { accessToken: undefined, userId: undefined },
  });

  expect(meCalls()).toHaveLength(0);

  rerender({ accessToken: "token-1", userId: "user-1" });

  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(meCalls()).toHaveLength(1);
});

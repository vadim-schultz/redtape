import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { LocaleProvider } from "../../../contexts/LocaleContext";
import { useSuggestionsListQuery } from "./useSuggestionsListQuery";

const fetchMock = vi.fn();

beforeEach(() => {
  window.localStorage.setItem("locale", "en");
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ items: [], total: 0, offset: 0, limit: 20 })),
  );
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={queryClient}>
      <LocaleProvider>{children}</LocaleProvider>
    </QueryClientProvider>
  );
}

function suggestionsCalls(): URL[] {
  return fetchMock.mock.calls
    .map(([url]) => new URL(String(url)))
    .filter((url) => url.pathname.endsWith("/api/v1/suggestions"));
}

it("useSuggestionsListQuery · fetches with the status filter", async () => {
  renderHook(
    () =>
      useSuggestionsListQuery({
        status: "approved",
        kind: null,
        jurisdictionId: null,
      }),
    { wrapper },
  );

  await waitFor(() => expect(suggestionsCalls()).not.toHaveLength(0));
  expect(suggestionsCalls()[0].searchParams.getAll("status")).toEqual([
    "approved",
  ]);
});

it("useSuggestionsListQuery · sends no status param for 'all'", async () => {
  renderHook(
    () =>
      useSuggestionsListQuery({
        status: "all",
        kind: null,
        jurisdictionId: null,
      }),
    { wrapper },
  );

  await waitFor(() => expect(suggestionsCalls()).not.toHaveLength(0));
  expect(suggestionsCalls()[0].searchParams.has("status")).toBe(false);
});

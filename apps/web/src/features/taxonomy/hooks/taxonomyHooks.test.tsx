import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { LocaleProvider, useLocale } from "../../../contexts/LocaleContext";
import { useCategoryTreeQuery } from "./useCategoryTreeQuery";

const fetchMock = vi.fn();

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <LocaleProvider>{children}</LocaleProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async () => new Response("[]"));
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

it("useCategoryTreeQuery · refetches when locale changes", async () => {
  const { result } = renderHook(
    () => ({ query: useCategoryTreeQuery(), locale: useLocale() }),
    { wrapper },
  );
  await waitFor(() => expect(result.current.query.isSuccess).toBe(true));
  const next = result.current.locale.locale === "de" ? "en" : "de";

  act(() => result.current.locale.setLocale(next));

  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).includes("/api/v1/categories"),
      ),
    ).toBe(true),
  );
});

it("category tree hook · returns roots and children from one query", async () => {
  fetchMock.mockImplementation(
    async () =>
      new Response(
        JSON.stringify([
          {
            code: "home-and-housing",
            name: "Home & housing",
            description: "",
            icon: "home",
            parent_code: null,
            children: [
              {
                code: "moving-house",
                name: "Moving house",
                description: "",
                icon: null,
                parent_code: "home-and-housing",
                children: [],
              },
            ],
          },
        ]),
      ),
  );

  const { result } = renderHook(() => useCategoryTreeQuery(), { wrapper });

  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.[0].children[0].code).toBe("moving-house");
  expect(
    fetchMock.mock.calls.filter(([url]) =>
      String(url).includes("/api/v1/categories"),
    ),
  ).toHaveLength(1);
});

it("category tree · failed query renders no stale tree data", async () => {
  fetchMock.mockImplementation(
    async () => new Response("boom", { status: 500 }),
  );

  const { result } = renderHook(() => useCategoryTreeQuery(), { wrapper });

  await waitFor(() => expect(result.current.isError).toBe(true));
  expect(result.current.data).toBeUndefined();
});

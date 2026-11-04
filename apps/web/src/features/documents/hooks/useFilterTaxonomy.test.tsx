import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";

import { LocaleProvider } from "../../../contexts/LocaleContext";
import { useFilterTaxonomy } from "./useFilterTaxonomy";

function renderTaxonomy() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <LocaleProvider>{children}</LocaleProvider>
    </QueryClientProvider>
  );
  return renderHook(() => useFilterTaxonomy(), { wrapper });
}

afterEach(() => vi.unstubAllGlobals());

it("category tree hook · returns roots and children from one query", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify([
            {
              code: "home-and-housing",
              name: "Home & housing",
              description: "",
              icon: "home",
              parent_code: null,
              children: [],
            },
          ]),
        ),
    ),
  );

  const { result } = renderTaxonomy();

  await waitFor(() => expect(result.current.categories).toHaveLength(1));
  expect(result.current.categories[0].code).toBe("home-and-housing");
  expect(result.current.isError).toBe(false);
});

it("category tree · failed query renders no stale chips", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response("boom", { status: 500 })),
  );

  const { result } = renderTaxonomy();

  await waitFor(() => expect(result.current.isError).toBe(true));
  expect(result.current.categories).toEqual([]);
});

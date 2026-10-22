import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";

import { LocaleProvider } from "../../../contexts/LocaleContext";
import { useFilterTaxonomy } from "./useFilterTaxonomy";

const term = (code: string) => ({
  code,
  name: code,
  description: "",
  icon: null,
});

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

it("useFilterTaxonomy · exposes domains and situations once loaded", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async (url: string) =>
        new Response(
          JSON.stringify(
            new URL(String(url)).pathname.endsWith("/domains")
              ? [term("housing")]
              : [term("moving")],
          ),
        ),
    ),
  );

  const { result } = renderTaxonomy();

  await waitFor(() => expect(result.current.domains).toHaveLength(1));
  expect(result.current.situations).toEqual([term("moving")]);
  expect(result.current.isError).toBe(false);
});

it("useFilterTaxonomy · flags an error when either query fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response("boom", { status: 500 })),
  );

  const { result } = renderTaxonomy();

  await waitFor(() => expect(result.current.isError).toBe(true));
  expect(result.current.domains).toEqual([]);
});

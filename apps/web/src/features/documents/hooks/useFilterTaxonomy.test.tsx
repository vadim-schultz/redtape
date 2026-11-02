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

function respond() {
  return vi.fn(async (url: string) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/domains"))
      return new Response(JSON.stringify([term("housing")]));
    if (path.endsWith("/life-situation-groups"))
      return new Response(JSON.stringify([term("home-housing")]));
    return new Response(JSON.stringify([term("moving")]));
  });
}

it("useFilterTaxonomy · exposes domains, situations and groups once loaded", async () => {
  vi.stubGlobal("fetch", respond());

  const { result } = renderTaxonomy();

  await waitFor(() => expect(result.current.domains).toHaveLength(1));
  expect(result.current.situations).toEqual([term("moving")]);
  expect(result.current.groups).toEqual([term("home-housing")]);
  expect(result.current.isError).toBe(false);
});

it("useFilterTaxonomy · flags an error when any query fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response("boom", { status: 500 })),
  );

  const { result } = renderTaxonomy();

  await waitFor(() => expect(result.current.isError).toBe(true));
  expect(result.current.domains).toEqual([]);
  expect(result.current.groups).toEqual([]);
});

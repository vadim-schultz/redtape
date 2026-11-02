import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { expect, it } from "vitest";

import { useDocumentFilters } from "./useDocumentFilters";

function renderFilters(url: string) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>
  );
  return renderHook(
    () => ({ filters: useDocumentFilters(), location: useLocation() }),
    { wrapper },
  );
}

it("useDocumentFilters · reads domains and situations from the URL", () => {
  const { result } = renderFilters("/documents?domain=a&domain=b&situation=x");

  expect(result.current.filters.domains).toEqual(["a", "b"]);
  expect(result.current.filters.situations).toEqual(["x"]);
});

it("useDocumentFilters · toggle adds then removes a code", () => {
  const { result } = renderFilters("/documents");

  act(() => result.current.filters.toggleDomain("a"));
  expect(result.current.location.search).toBe("?domain=a");
  expect(result.current.filters.domains).toEqual(["a"]);

  act(() => result.current.filters.toggleDomain("a"));
  expect(result.current.location.search).toBe("");
});

it("useDocumentFilters · toggling one axis keeps the other", () => {
  const { result } = renderFilters("/documents?situation=x");

  act(() => result.current.filters.toggleDomain("a"));

  expect(result.current.filters.situations).toEqual(["x"]);
  expect(result.current.filters.domains).toEqual(["a"]);
});

it("useDocumentFilters · ignores empty and duplicate values", () => {
  const { result } = renderFilters("/documents?domain=&domain=a&domain=a");

  expect(result.current.filters.domains).toEqual(["a"]);
});

it("useDocumentFilters · clear removes all filters", () => {
  const { result } = renderFilters("/documents?domain=a&situation=x");

  act(() => result.current.filters.clear());

  expect(result.current.location.search).toBe("");
});

it("useDocumentFilters · a toggle returns to the first page", () => {
  const { result } = renderFilters("/documents?domain=a&offset=40&q=pass");

  act(() => result.current.filters.toggleSituation("x"));

  const params = new URLSearchParams(result.current.location.search);
  expect(params.has("offset")).toBe(false);
  expect(params.get("q")).toBe("pass");
  expect(params.getAll("domain")).toEqual(["a"]);
});

it("useDocumentFilters · clear drops filters and the page but keeps search and sort", () => {
  const { result } = renderFilters(
    "/documents?domain=a&situation=x&offset=40&q=pass&sort_by=title",
  );

  act(() => result.current.filters.clear());

  const params = new URLSearchParams(result.current.location.search);
  expect([...params.keys()].sort()).toEqual(["q", "sort_by"]);
});

it("useDocumentFilters · clearAll also removes the search term", () => {
  const { result } = renderFilters(
    "/documents?domain=a&offset=40&q=pass&sort_by=title",
  );

  act(() => result.current.filters.clearAll());

  const params = new URLSearchParams(result.current.location.search);
  expect([...params.keys()]).toEqual(["sort_by"]);
});

it("useDocumentFilters · the old leaf param is not a filter any more", () => {
  const { result } = renderFilters("/documents?leaf=1050200");

  expect(result.current.filters).not.toHaveProperty("leaves");
  expect(result.current.filters).not.toHaveProperty("toggleLeaf");
});

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

it("useDocumentFilters · reads leaf codes from the URL", () => {
  const { result } = renderFilters("/documents?leaf=1050200");

  expect(result.current.filters.leaves).toEqual(["1050200"]);
});

it("useDocumentFilters · toggleLeaf adds then removes a leaf code", () => {
  const { result } = renderFilters("/documents");

  act(() => result.current.filters.toggleLeaf("1050200"));
  expect(result.current.location.search).toBe("?leaf=1050200");

  act(() => result.current.filters.toggleLeaf("1050200"));
  expect(result.current.location.search).toBe("");
});

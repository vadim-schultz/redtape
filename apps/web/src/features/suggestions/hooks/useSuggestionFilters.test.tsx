import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { expect, it } from "vitest";

import { useSuggestionFilters } from "./useSuggestionFilters";

function renderFilters(url: string) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>
  );
  return renderHook(
    () => ({ filters: useSuggestionFilters(), location: useLocation() }),
    { wrapper },
  );
}

it("useSuggestionFilters · defaults to pending with no query string", () => {
  const { result } = renderFilters("/suggestions");

  expect(result.current.filters.status).toBe("pending");
});

it("useSuggestionFilters · reads status, kind and jurisdiction_id from the URL", () => {
  const { result } = renderFilters(
    "/suggestions?status=approved&kind=new_document&jurisdiction_id=j1",
  );

  expect(result.current.filters.status).toBe("approved");
  expect(result.current.filters.kind).toBe("new_document");
  expect(result.current.filters.jurisdictionId).toBe("j1");
});

it("useSuggestionFilters · an unknown status falls back to pending", () => {
  const { result } = renderFilters("/suggestions?status=bogus");

  expect(result.current.filters.status).toBe("pending");
});

it("useSuggestionFilters · status=all is kept", () => {
  const { result } = renderFilters("/suggestions?status=all");

  expect(result.current.filters.status).toBe("all");
});

it("useSuggestionFilters · an unknown kind is null", () => {
  const { result } = renderFilters("/suggestions?kind=bogus");

  expect(result.current.filters.kind).toBeNull();
});

it("useSuggestionFilters · a known kind is kept", () => {
  const { result } = renderFilters("/suggestions?kind=new_requirement");

  expect(result.current.filters.kind).toBe("new_requirement");
});

it("useSuggestionFilters · setStatus keeps an unknown kind out of the URL", () => {
  const { result } = renderFilters("/suggestions?kind=bogus");

  act(() => result.current.filters.setStatus("approved"));

  expect(result.current.location.search).toBe("?status=approved");
});

it("useSuggestionFilters · setStatus updates the URL", () => {
  const { result } = renderFilters("/suggestions");

  act(() => result.current.filters.setStatus("approved"));
  expect(result.current.location.search).toBe("?status=approved");

  act(() => result.current.filters.setStatus("pending"));
  expect(result.current.location.search).toBe("");
});

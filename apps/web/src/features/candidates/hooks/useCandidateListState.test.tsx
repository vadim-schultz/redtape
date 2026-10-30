import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";

import { useCandidateListState } from "./useCandidateListState";

function renderState(url: string) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>
  );
  return renderHook(() => useCandidateListState(), { wrapper });
}

it("candidate list state resets the offset on a filter change", () => {
  const { result } = renderState(
    "/candidates?offset=40&filter[situation]=moving",
  );

  act(() => result.current.setFilter("domain", "identity"));

  expect(result.current.state.offset).toBe(0);
  expect(result.current.state.filters).toEqual({
    situation: "moving",
    domain: "identity",
  });
});

it("candidate list state keeps the filter when only the page changes", () => {
  const { result } = renderState("/candidates?filter[domain]=identity");

  act(() => result.current.setOffset(20));

  expect(result.current.state.offset).toBe(20);
  expect(result.current.state.filters).toEqual({ domain: "identity" });
});

it("candidate list state ignores a value the api would refuse", () => {
  const { result } = renderState(
    "/candidates?filter[complete]=maybe&offset=20",
  );

  expect(result.current.state.filters).toEqual({});
  expect(result.current.state.offset).toBe(20);
});

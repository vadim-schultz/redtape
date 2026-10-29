import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { expect, it } from "vitest";

import type { ListQuerySpec } from "../services/listQuery";
import { useListQueryState } from "./useListQueryState";

type Sort = "name";
type Filter = "colour";

const SPEC: ListQuerySpec<Sort, Filter> = {
  sortKeys: ["name"],
  filters: { colour: (raw) => (raw === "red" ? raw : undefined) },
  defaultLimit: 20,
  maxLimit: 100,
};

function renderState(url: string) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>
  );
  return renderHook(
    () => ({ list: useListQueryState(SPEC), location: useLocation() }),
    { wrapper },
  );
}

it("list query state reads the validated state from the url", () => {
  const { result } = renderState("/x?offset=40&filter[colour]=red&sort_by=bad");
  expect(result.current.list.state).toEqual({
    offset: 40,
    limit: 20,
    filters: { colour: "red" },
  });
});

it("list query state writes sort and filter changes to the url at the first page", () => {
  const { result } = renderState("/x?offset=40&tab=1");

  act(() => result.current.list.setSort({ sortBy: "name", sortOrder: "desc" }));
  expect(result.current.location.search).toBe(
    "?tab=1&sort_by=name&sort_order=desc",
  );

  act(() => result.current.list.setFilter("colour", "red"));
  expect(result.current.list.state.filters).toEqual({ colour: "red" });
  expect(result.current.list.state.offset).toBe(0);
});

it("list query state keeps the other parameters and pages without a reset", () => {
  const { result } = renderState("/x?tab=1&q=pass");

  act(() => result.current.list.setOffset(20));

  expect(result.current.location.search).toBe("?tab=1&offset=20&q=pass");
  expect(result.current.list.state.search).toBe("pass");
});

it("list query state clears every filter from the url and returns to the first page", () => {
  const { result } = renderState(
    "/x?offset=40&filter[colour]=red&q=pass&tab=1",
  );

  act(() => result.current.list.clearFilters());

  expect(result.current.location.search).toBe("?tab=1&q=pass");
  expect(result.current.list.state.filters).toEqual({});
});

it("list query state ignores a filter the spec rejects, so clearing starts from the valid state", () => {
  const { result } = renderState("/x?filter[colour]=green&offset=20");

  act(() => result.current.list.clearFilters());

  expect(result.current.location.search).toBe("");
});

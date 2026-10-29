import { expect, it, vi } from "vitest";

import { fakeListController } from "../test/fakeListController";
import type { ListQueryController } from "./useListQueryState";
import { toTableQuery } from "./toTableQuery";

type Sort = "name";
type Filter = "colour";

function controller(
  state: Partial<ListQueryController<Sort, Filter>["state"]> = {},
) {
  return fakeListController<Sort, Filter>(state);
}

it("table query shows the applied sort and filters of the list state", () => {
  const list = controller({
    sortBy: "name",
    sortOrder: "desc",
    filters: { colour: "red" },
  });

  const query = toTableQuery(list);

  expect(query.sort).toEqual({ sortBy: "name", sortOrder: "desc" });
  expect(query.filters).toEqual({ colour: "red" });
});

it("table query shows the fallback sort only while the state has none", () => {
  const fallback = { sortBy: "name", sortOrder: "asc" } as const;

  expect(toTableQuery(controller(), fallback).sort).toEqual(fallback);
  expect(
    toTableQuery(controller({ sortBy: "name", sortOrder: "desc" }), fallback)
      .sort,
  ).toEqual({ sortBy: "name", sortOrder: "desc" });
  expect(toTableQuery(controller()).sort).toEqual({});
});

it("table query routes table events to the list controller", () => {
  const list = controller();
  const query = toTableQuery(list);

  query.onSortChange?.({ sortBy: "name", sortOrder: "asc" });
  query.onFilterChange?.({ key: "colour", value: "red" });
  query.onFilterChange?.({ key: "colour", value: "" });
  query.onFiltersClear?.();

  expect(vi.mocked(list.setSort)).toHaveBeenCalledWith({
    sortBy: "name",
    sortOrder: "asc",
  });
  expect(vi.mocked(list.setFilter).mock.calls).toEqual([
    ["colour", "red"],
    ["colour", undefined],
  ]);
  expect(vi.mocked(list.clearFilters)).toHaveBeenCalledOnce();
});

import { describe, expect, it } from "vitest";

import {
  parseListUrl,
  serializeListUrl,
  toListParams,
  withFilter,
  withOffset,
  withSearch,
  withSort,
  type ListQuerySpec,
  type ListQueryState,
} from "./index";

type Sort = "name" | "created_at";
type Filter = "colour" | "min_size";

const oneOf =
  (...values: string[]) =>
  (raw: string) =>
    values.includes(raw) ? raw : undefined;

const minSize = (raw: string) => {
  const value = Number(raw);
  return Number.isInteger(value) && value >= 0 ? value : undefined;
};

const SPEC: ListQuerySpec<Sort, Filter> = {
  sortKeys: ["name", "created_at"],
  filters: { colour: oneOf("red", "blue"), min_size: minSize },
  defaultLimit: 20,
  maxLimit: 100,
};

const BASE: ListQueryState<Sort, Filter> = {
  offset: 40,
  limit: 20,
  sortBy: "name",
  sortOrder: "desc",
  search: "pass",
  filters: { colour: "red", min_size: 3 },
};

describe("query state serialization", () => {
  it("query state serializes canonical list parameters", () => {
    expect(toListParams(BASE)).toEqual({
      offset: 40,
      limit: 20,
      sort_by: "name",
      sort_order: "desc",
      q: "pass",
      "filter[colour]": "red",
      "filter[min_size]": 3,
    });
  });

  it("query state leaves unset sort, search and filters out of the parameters", () => {
    const state = { ...BASE, sortBy: undefined, search: "", filters: {} };
    expect(toListParams({ ...state, sortOrder: "asc" })).toEqual({
      offset: 40,
      limit: 20,
    });
    expect(
      toListParams({ ...state, filters: { colour: undefined } }),
    ).not.toHaveProperty("filter[colour]");
  });

  it("query state sorts ascending when only a sort key is set", () => {
    const state = { ...BASE, sortOrder: undefined };
    expect(toListParams(state).sort_order).toBe("asc");
  });
});

describe("query state transitions", () => {
  it("query state resets offset when sort or filter changes", () => {
    expect(withSort(BASE, { sortBy: "created_at", sortOrder: "asc" })).toEqual({
      ...BASE,
      sortBy: "created_at",
      sortOrder: "asc",
      offset: 0,
    });
    expect(withFilter(BASE, "colour", "blue").offset).toBe(0);
    expect(withFilter(BASE, "colour", undefined).filters).toEqual({
      min_size: 3,
    });
    expect(withSearch(BASE, "visa")).toMatchObject({
      search: "visa",
      offset: 0,
    });
  });

  it("query state keeps the offset when only the page changes", () => {
    expect(withOffset(BASE, 60)).toEqual({ ...BASE, offset: 60 });
    expect(withOffset(BASE, -5).offset).toBe(0);
  });
});

describe("list URL state", () => {
  it("list url round-trips a state and omits defaults", () => {
    const params = serializeListUrl(BASE, SPEC);
    expect(params.toString()).toBe(
      "offset=40&sort_by=name&sort_order=desc&q=pass&filter%5Bcolour%5D=red&filter%5Bmin_size%5D=3",
    );
    expect(parseListUrl(params, SPEC)).toEqual(BASE);
    expect(
      serializeListUrl({ ...BASE, offset: 0, filters: {} }, SPEC).has("offset"),
    ).toBe(false);
  });

  it("list url keeps parameters it does not own and replaces the ones it does", () => {
    const current = new URLSearchParams("tab=x&offset=20&filter[colour]=blue");
    const next = serializeListUrl({ ...BASE, filters: {} }, SPEC, current);
    expect(next.get("tab")).toBe("x");
    expect(next.getAll("offset")).toEqual(["40"]);
    expect(next.has("filter[colour]")).toBe(false);
  });

  it("list url rejects invalid values to defaults", () => {
    const params = new URLSearchParams(
      "offset=-3&limit=9999&sort_by=password&sort_order=up&q=%20%20&filter[colour]=green&filter[min_size]=x&filter[other]=1",
    );
    expect(parseListUrl(params, SPEC)).toEqual({
      offset: 0,
      limit: 20,
      filters: {},
    });
  });

  it("list url ignores a sort order without a valid sort key", () => {
    const parsed = parseListUrl(
      new URLSearchParams("sort_order=desc&limit=50"),
      SPEC,
    );
    expect(parsed).toEqual({ offset: 0, limit: 50, filters: {} });
    expect(
      parseListUrl(new URLSearchParams("sort_by=name"), SPEC).sortOrder,
    ).toBe("asc");
  });
});

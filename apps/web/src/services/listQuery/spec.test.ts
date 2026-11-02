import { expect, it } from "vitest";

import { oneOfFilter } from "./filters";
import { defineListSpec } from "./spec";

const SORT_KEYS = ["title", "created_at"] as const;

it("defineListSpec · applies 20 and 100 as default and max limit", () => {
  const spec = defineListSpec({ sortKeys: SORT_KEYS, filters: {} });

  expect(spec.defaultLimit).toBe(20);
  expect(spec.maxLimit).toBe(100);
});

it("defineListSpec · keeps explicit limits", () => {
  const spec = defineListSpec({
    sortKeys: SORT_KEYS,
    filters: {},
    defaultLimit: 10,
    maxLimit: 50,
  });

  expect(spec.defaultLimit).toBe(10);
  expect(spec.maxLimit).toBe(50);
});

it("defineListSpec · keeps sortKeys and filters as given", () => {
  const statusFilter = oneOfFilter(["open", "closed"]);
  const spec = defineListSpec({
    sortKeys: SORT_KEYS,
    filters: { status: statusFilter },
  });

  expect(spec.sortKeys).toBe(SORT_KEYS);
  expect(spec.filters.status).toBe(statusFilter);
});

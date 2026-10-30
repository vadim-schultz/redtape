import { expect, it } from "vitest";

import { hasActiveFilters } from "./hasActiveFilters";

const base = { offset: 0, limit: 20 };

it("has active filters when a filter is set", () => {
  expect(hasActiveFilters({ ...base, filters: { domain: "identity" } })).toBe(
    true,
  );
});

it("has no active filters for an empty filter set, even with a search", () => {
  expect(hasActiveFilters({ ...base, search: "pass", filters: {} })).toBe(
    false,
  );
});

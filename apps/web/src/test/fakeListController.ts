import { vi } from "vitest";

import type { ListQueryController } from "../hooks/useListQueryState";

/** A list controller whose setters are spies, over a state with the given overrides. */
export function fakeListController<
  SortKey extends string,
  FilterKey extends string,
>(
  state: Partial<ListQueryController<SortKey, FilterKey>["state"]> = {},
): ListQueryController<SortKey, FilterKey> {
  return {
    state: { offset: 0, limit: 20, filters: {}, ...state },
    setSort: vi.fn(),
    setSearch: vi.fn(),
    setFilter: vi.fn(),
    clearFilters: vi.fn(),
    setOffset: vi.fn(),
  };
}

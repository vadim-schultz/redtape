import type { ListParams, ListQueryState } from "./types";

/** The wire name of one filter, e.g. `filter[source]`. */
export const filterParam = (key: string) => `filter[${key}]`;

function sortParams(state: ListQueryState<string, string>): ListParams {
  if (!state.sortBy) return {};
  return { sort_by: state.sortBy, sort_order: state.sortOrder ?? "asc" };
}

function searchParams(state: ListQueryState<string, string>): ListParams {
  return state.search ? { q: state.search } : {};
}

function filterParams(state: ListQueryState<string, string>): ListParams {
  const entries = Object.entries(state.filters).flatMap(([key, value]) =>
    value === undefined || value === "" ? [] : [[filterParam(key), value]],
  );
  return Object.fromEntries(entries) as ListParams;
}

/** The canonical API/URL parameters of a state; unset sort, search and filters are left out. */
export function toListParams<SortKey extends string, FilterKey extends string>(
  state: ListQueryState<SortKey, FilterKey>,
): ListParams {
  return {
    offset: state.offset,
    limit: state.limit,
    ...sortParams(state),
    ...searchParams(state),
    ...filterParams(state),
  };
}

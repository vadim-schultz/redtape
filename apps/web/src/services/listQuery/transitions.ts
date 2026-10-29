import type {
  FilterValue,
  ListQueryState,
  SortChange,
  SortOrder,
} from "./types";

type State<S extends string, F extends string> = ListQueryState<S, F>;

/** A query-shaping change always returns to the first page. */
function reshaped<S extends string, F extends string>(
  state: State<S, F>,
  patch: Partial<State<S, F>>,
): State<S, F> {
  return { ...state, ...patch, offset: 0 };
}

/** Apply a sort change (as the DataTable emits it) and return to the first page. */
export function withSort<S extends string, F extends string>(
  state: State<S, F>,
  sort: SortChange<S>,
): State<S, F> {
  const sortOrder: SortOrder | undefined = sort.sortBy
    ? (sort.sortOrder ?? "asc")
    : undefined;
  return reshaped(state, { sortBy: sort.sortBy, sortOrder });
}

/** Apply a search term and return to the first page. */
export function withSearch<S extends string, F extends string>(
  state: State<S, F>,
  search: string,
): State<S, F> {
  return reshaped(state, { search: search.trim() || undefined });
}

/** Set (or clear, with `undefined`) one filter and return to the first page. */
export function withFilter<S extends string, F extends string>(
  state: State<S, F>,
  key: F,
  value: FilterValue | undefined,
): State<S, F> {
  const kept = Object.entries(state.filters).filter(([name]) => name !== key);
  const filters = Object.fromEntries(
    value === undefined ? kept : [...kept, [key, value]],
  );
  return reshaped(state, { filters: filters as State<S, F>["filters"] });
}

/** Move to another page; the only change that keeps the rest of the query. */
export function withOffset<S extends string, F extends string>(
  state: State<S, F>,
  offset: number,
): State<S, F> {
  return { ...state, offset: Math.max(0, offset) };
}

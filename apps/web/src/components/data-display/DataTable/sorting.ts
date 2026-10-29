import type { SortState } from "./types";

type AriaSort = "ascending" | "descending" | "none";

/** The sort after a user activates `key`: toggle the active column, else start ascending. */
export function nextSort<SortKey extends string>(
  current: SortState<SortKey>,
  key: SortKey,
): SortState<SortKey> {
  const flip = current.sortBy === key && current.sortOrder === "asc";
  return { sortBy: key, sortOrder: flip ? "desc" : "asc" };
}

/** `aria-sort` for a header: undefined for display columns, so none is announced. */
export function ariaSortFor<SortKey extends string>(
  current: SortState<SortKey>,
  key: SortKey | undefined,
): AriaSort | undefined {
  if (!key) return undefined;
  if (current.sortBy !== key) return "none";
  return current.sortOrder === "desc" ? "descending" : "ascending";
}

import type { FilterValue, ListQuerySpec } from "./types";

interface ListSpecInput<SortKey extends string, FilterKey extends string> {
  sortKeys: readonly SortKey[];
  filters: Record<FilterKey, (raw: string) => FilterValue | undefined>;
  defaultLimit?: number;
  maxLimit?: number;
}

/** Builds a list spec with the shared page-size defaults; infers both key unions from its arguments. */
export function defineListSpec<
  SortKey extends string,
  FilterKey extends string,
>({
  sortKeys,
  filters,
  defaultLimit = 20,
  maxLimit = 100,
}: ListSpecInput<SortKey, FilterKey>): ListQuerySpec<SortKey, FilterKey> {
  return { sortKeys, filters, defaultLimit, maxLimit };
}

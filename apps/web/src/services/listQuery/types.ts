export type SortOrder = "asc" | "desc";

/** A filter value as it travels on the wire; multi-value filters are not part of the contract yet. */
export type FilterValue = string | number;

/** Typed table query state; serialized to one canonical URL and API shape. */
export interface ListQueryState<
  SortKey extends string,
  FilterKey extends string,
> {
  offset: number;
  limit: number;
  sortBy?: SortKey;
  sortOrder?: SortOrder;
  search?: string;
  filters: Partial<Record<FilterKey, FilterValue | undefined>>;
}

/** A sort a table emits; structurally the same as the DataTable's sort state. */
export interface SortChange<SortKey extends string> {
  sortBy?: SortKey;
  sortOrder?: SortOrder;
}

/** What one resource allows: sort keys, a validating parser per filter, and the page-size bounds. */
export interface ListQuerySpec<
  SortKey extends string,
  FilterKey extends string,
> {
  sortKeys: readonly SortKey[];
  /** Each parser returns the typed value, or `undefined` to reject the raw text. */
  filters: Record<FilterKey, (raw: string) => FilterValue | undefined>;
  defaultLimit: number;
  maxLimit: number;
}

export type ListParams = Record<string, string | number>;

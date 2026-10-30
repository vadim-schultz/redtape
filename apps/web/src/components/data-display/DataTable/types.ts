import type { ReactNode } from "react";

import type { QueryStatus } from "../../feedback/queryStatus";

export type SortOrder = "asc" | "desc";

export type FilterOperator = "eq" | "contains" | "in" | "gte" | "lte";

/** The sort the parent currently applies; empty means unsorted. */
export interface SortState<SortKey extends string> {
  sortBy?: SortKey;
  sortOrder?: SortOrder;
}

/** One value of a bounded filter and the text shown for it. */
export interface FilterOption {
  value: string;
  label: string;
}

/** A column's filter capability: the server key, operators, and control name. */
export interface FilterCapability<FilterKey extends string> {
  key: FilterKey;
  operators: readonly FilterOperator[];
  /** Accessible name of the filter control; also names the filter in the applied summary. */
  label: string;
  /** The allowed values of a bounded field; without them the filter takes free text. */
  options?: readonly FilterOption[];
}

/** The filter value a user applied for one declared filter key; an empty value removes the filter. */
export interface FilterChange<FilterKey extends string> {
  key: FilterKey;
  value: string;
}

/** Horizontal alignment of a column's header and cells; numeric columns use `end`. */
export type ColumnAlign = "start" | "center" | "end";

/** A column declares its sort/filter capability; display columns declare none. */
export interface DataTableColumn<
  Row,
  SortKey extends string,
  FilterKey extends string,
> {
  key: string;
  header: ReactNode;
  canSort?: SortKey;
  filter?: FilterCapability<FilterKey>;
  align?: ColumnAlign;
  /** Upper bound of the column's cells (a size token or CSS length); overflow is clipped. */
  maxWidth?: string;
  render: (row: Row) => ReactNode;
}

/** Rows to show, how to key them, and where a row navigates (if anywhere). */
export interface DataTableRows<Row> {
  items: readonly Row[];
  getKey: (row: Row) => string;
  getHref?: (row: Row) => string;
}

/** The filter values the parent currently applies; absent or empty means not filtered. */
export type AppliedFilters<FilterKey extends string> = Partial<
  Record<FilterKey, string | number | undefined>
>;

/** Applied sort and filters, and the typed events the table emits to the parent's query hook. */
export interface DataTableQuery<
  SortKey extends string,
  FilterKey extends string,
> {
  sort?: SortState<SortKey>;
  onSortChange?: (next: SortState<SortKey>) => void;
  filters?: AppliedFilters<FilterKey>;
  onFilterChange?: (change: FilterChange<FilterKey>) => void;
  onFiltersClear?: () => void;
}

/** Opt-in state slots; each missing slot falls back to a shared default. */
export interface DataTableStates {
  status?: QueryStatus;
  loading?: ReactNode;
  empty?: ReactNode;
  error?: ReactNode;
}

/** Offset paging of the complete filtered result. */
export interface DataTablePage {
  offset: number;
  limit: number;
  total: number;
  onOffsetChange: (offset: number) => void;
}

export interface DataTableProps<
  Row,
  SortKey extends string,
  FilterKey extends string,
> {
  /** Accessible name of the table. */
  label: string;
  columns: readonly DataTableColumn<Row, SortKey, FilterKey>[];
  rows: DataTableRows<Row>;
  query?: DataTableQuery<SortKey, FilterKey>;
  states?: DataTableStates;
  page?: DataTablePage;
}

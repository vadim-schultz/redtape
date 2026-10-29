import type { ReactNode } from "react";

import type { QueryStatus } from "../../feedback/queryStatus";

export type SortOrder = "asc" | "desc";

export type FilterOperator = "eq" | "contains" | "in" | "gte" | "lte";

/** The sort the parent currently applies; empty means unsorted. */
export interface SortState<SortKey extends string> {
  sortBy?: SortKey;
  sortOrder?: SortOrder;
}

/** A column's filter capability: the server key, operators, and control name. */
export interface FilterCapability<FilterKey extends string> {
  key: FilterKey;
  operators: readonly FilterOperator[];
  /** Accessible name of the filter control. */
  label: string;
}

/** The filter value a user entered for one declared filter key. */
export interface FilterChange<FilterKey extends string> {
  key: FilterKey;
  value: string;
}

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
  render: (row: Row) => ReactNode;
}

/** Rows to show, how to key them, and where a row navigates (if anywhere). */
export interface DataTableRows<Row> {
  items: readonly Row[];
  getKey: (row: Row) => string;
  getHref?: (row: Row) => string;
}

/** Sort state and the typed events the table emits to the parent's query hook. */
export interface DataTableQuery<
  SortKey extends string,
  FilterKey extends string,
> {
  sort?: SortState<SortKey>;
  onSortChange?: (next: SortState<SortKey>) => void;
  onFilterChange?: (change: FilterChange<FilterKey>) => void;
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

import type {
  DataTableQuery,
  SortState,
} from "../components/data-display/DataTable";
import type { ListQueryController } from "./useListQueryState";

/**
 * The DataTable query props of a URL-backed list: applied sort and filters, and
 * the table's events routed to the list controller. `fallbackSort` is the order
 * the API applies when the URL names none, so the header can show it.
 */
export function toTableQuery<SortKey extends string, FilterKey extends string>(
  list: ListQueryController<SortKey, FilterKey>,
  fallbackSort?: SortState<SortKey>,
): DataTableQuery<SortKey, FilterKey> {
  const { sortBy, sortOrder, filters } = list.state;
  return {
    sort: sortBy ? { sortBy, sortOrder } : (fallbackSort ?? {}),
    onSortChange: list.setSort,
    filters,
    onFilterChange: ({ key, value }) => list.setFilter(key, value || undefined),
    onFiltersClear: list.clearFilters,
  };
}

import ActiveFilters from "./ActiveFilters";
import { activeFilters } from "./filters";
import RefetchError from "./RefetchError";
import type { TableState } from "./tableState";
import type { DataTableColumn, DataTableQuery, DataTableStates } from "./types";

export interface DataTableFeedbackProps<
  Row,
  SortKey extends string,
  FilterKey extends string,
> {
  state: TableState;
  columns: readonly DataTableColumn<Row, SortKey, FilterKey>[];
  query: DataTableQuery<SortKey, FilterKey>;
  states: DataTableStates;
}

/** What the table says about its query above the rows: applied filters, and a failed refresh. */
export default function DataTableFeedback<
  Row,
  SortKey extends string,
  FilterKey extends string,
>({
  state,
  columns,
  query,
  states,
}: DataTableFeedbackProps<Row, SortKey, FilterKey>) {
  const { onFilterChange, onFiltersClear, filters } = query;
  const refetchFailed =
    states.status?.isError === true && state === "populated";

  return (
    <>
      {onFilterChange ? (
        <ActiveFilters
          filters={activeFilters(columns, filters)}
          onRemove={(key) => onFilterChange({ key, value: "" })}
          onClear={onFiltersClear}
        />
      ) : null}
      {refetchFailed ? (
        <RefetchError onRetry={() => states.status?.onRetry()} />
      ) : null}
    </>
  );
}

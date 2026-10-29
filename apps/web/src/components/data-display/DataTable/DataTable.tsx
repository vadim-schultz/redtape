import { Stack, Table } from "@chakra-ui/react";

import Pagination from "../Pagination";
import DataTableBody from "./DataTableBody";
import DataTableFeedback from "./DataTableFeedback";
import DataTableHeader from "./DataTableHeader";
import ScrollRegion from "./ScrollRegion";
import { resolveTableState } from "./tableState";
import type { DataTableProps } from "./types";

/**
 * The single table presentation primitive. The parent owns query state; the
 * table renders typed columns, emits typed sort/filter/page events, and shows
 * loading, error, empty, populated, and refreshing states.
 */
export default function DataTable<
  Row,
  SortKey extends string,
  FilterKey extends string,
>({
  label,
  columns,
  rows,
  query = {},
  states = {},
  page,
}: DataTableProps<Row, SortKey, FilterKey>) {
  const state = resolveTableState(states, rows.items.length);
  const refreshing = states.status?.isRefreshing ?? false;

  return (
    <Stack gap={3}>
      <DataTableFeedback
        state={state}
        columns={columns}
        query={query}
        states={states}
      />
      <ScrollRegion label={label}>
        <Table.Root
          size="sm"
          aria-label={label}
          aria-busy={refreshing || state === "loading"}
          opacity={refreshing ? 0.6 : 1}
          transition="opacity 0.2s"
        >
          <DataTableHeader columns={columns} query={query} />
          <DataTableBody
            state={state}
            columns={columns}
            rows={rows}
            states={states}
          />
        </Table.Root>
      </ScrollRegion>
      {page && state === "populated" ? <Pagination {...page} /> : null}
    </Stack>
  );
}

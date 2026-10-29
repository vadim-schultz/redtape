import { Table } from "@chakra-ui/react";

import DataTableRow from "./DataTableRow";
import DataTableStateView from "./DataTableStateView";
import type { TableState } from "./tableState";
import type { DataTableColumn, DataTableRows, DataTableStates } from "./types";

export interface DataTableBodyProps<
  Row,
  SortKey extends string,
  FilterKey extends string,
> {
  state: TableState;
  columns: readonly DataTableColumn<Row, SortKey, FilterKey>[];
  rows: DataTableRows<Row>;
  states: DataTableStates;
}

/** Body rows when populated; otherwise one full-width row holding the state slot. */
export default function DataTableBody<
  Row,
  SortKey extends string,
  FilterKey extends string,
>({
  state,
  columns,
  rows,
  states,
}: DataTableBodyProps<Row, SortKey, FilterKey>) {
  if (state !== "populated") {
    return (
      <Table.Body>
        <Table.Row>
          <Table.Cell colSpan={columns.length}>
            <DataTableStateView state={state} states={states} />
          </Table.Cell>
        </Table.Row>
      </Table.Body>
    );
  }

  return (
    <Table.Body>
      {rows.items.map((row) => (
        <DataTableRow
          key={rows.getKey(row)}
          row={row}
          columns={columns}
          href={rows.getHref?.(row)}
        />
      ))}
    </Table.Body>
  );
}

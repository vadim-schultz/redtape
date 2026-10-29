import { Table } from "@chakra-ui/react";

import { useRowNavigation } from "./rowNavigation";
import type { DataTableColumn } from "./types";

export interface DataTableRowProps<
  Row,
  SortKey extends string,
  FilterKey extends string,
> {
  row: Row;
  columns: readonly DataTableColumn<Row, SortKey, FilterKey>[];
  href?: string;
}

/** One body row; navigates to `href` when given, leaving nested controls alone. */
export default function DataTableRow<
  Row,
  SortKey extends string,
  FilterKey extends string,
>({ row, columns, href }: DataTableRowProps<Row, SortKey, FilterKey>) {
  const navigation = useRowNavigation(href);

  return (
    <Table.Row
      backgroundColor="table.row.bg"
      _hover={href ? { backgroundColor: "table.row.hover" } : undefined}
      {...navigation}
    >
      {columns.map((column) => (
        <Table.Cell key={column.key} textStyle="body">
          {column.render(row)}
        </Table.Cell>
      ))}
    </Table.Row>
  );
}

import { Table } from "@chakra-ui/react";

import { ColumnFilter, SortButton } from "./ColumnControls";
import { ariaSortFor, nextSort } from "./sorting";
import type { DataTableColumn, DataTableQuery } from "./types";

export interface DataTableHeaderProps<
  Row,
  SortKey extends string,
  FilterKey extends string,
> {
  columns: readonly DataTableColumn<Row, SortKey, FilterKey>[];
  query: DataTableQuery<SortKey, FilterKey>;
}

type CellProps<Row, SortKey extends string, FilterKey extends string> = {
  column: DataTableColumn<Row, SortKey, FilterKey>;
  query: DataTableQuery<SortKey, FilterKey>;
};

function HeaderCell<Row, SortKey extends string, FilterKey extends string>({
  column: { canSort, filter, header },
  query: { sort = {}, onSortChange, onFilterChange },
}: CellProps<Row, SortKey, FilterKey>) {
  const sortable = canSort !== undefined && onSortChange !== undefined;
  const filterable = filter !== undefined && onFilterChange !== undefined;

  return (
    <Table.ColumnHeader
      textStyle="tableHeader"
      backgroundColor="table.header.bg"
      aria-sort={sortable ? ariaSortFor(sort, canSort) : undefined}
    >
      {sortable ? (
        <SortButton
          header={header}
          order={sort.sortBy === canSort ? sort.sortOrder : undefined}
          onSort={() => onSortChange(nextSort(sort, canSort))}
        />
      ) : (
        header
      )}
      {filterable ? (
        <ColumnFilter
          filter={filter}
          onChange={(value) => onFilterChange({ key: filter.key, value })}
        />
      ) : null}
    </Table.ColumnHeader>
  );
}

/** Header row; sort and filter controls appear only where a column declares them. */
export default function DataTableHeader<
  Row,
  SortKey extends string,
  FilterKey extends string,
>({ columns, query }: DataTableHeaderProps<Row, SortKey, FilterKey>) {
  return (
    <Table.Header>
      <Table.Row>
        {columns.map((column) => (
          <HeaderCell key={column.key} column={column} query={query} />
        ))}
      </Table.Row>
    </Table.Header>
  );
}

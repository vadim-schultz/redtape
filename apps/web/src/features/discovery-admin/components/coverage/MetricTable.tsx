import { Badge, HStack, Text } from "@chakra-ui/react";

import {
  DataTable,
  type DataTableColumn,
} from "../../../../components/data-display/DataTable";
import type { MetricCell, MetricGroup, MetricRow } from "./metricModel";

type MetricColumn = DataTableColumn<MetricRow, never, never>;

function CellView({ cell }: { cell: MetricCell }) {
  return (
    <HStack gap={2}>
      <Text fontVariantNumeric="tabular-nums">{cell.text}</Text>
      {cell.badge ? (
        <Badge variant="subtle" colorPalette={cell.badge.palette}>
          {cell.badge.label}
        </Badge>
      ) : null}
    </HStack>
  );
}

function columnsOf(headers: string[]): MetricColumn[] {
  return headers.map((header, index) => ({
    key: `column_${index}`,
    header,
    render: (row) =>
      index === 0 ? row.label : <CellView cell={row.cells[index - 1]} />,
  }));
}

/**
 * One metric group as a static table: a stable label column then its values.
 * It declares no sort or filter, so the table shows none.
 */
export default function MetricTable({ group }: { group: MetricGroup }) {
  return (
    <DataTable
      label={group.title}
      columns={columnsOf(group.headers)}
      rows={{ items: group.rows, getKey: (row) => row.key }}
      states={{ empty: <Text color="fg.muted">{group.emptyText}</Text> }}
    />
  );
}

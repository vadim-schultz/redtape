import { Badge } from "@chakra-ui/react";

import {
  DataTable,
  type DataTableColumn,
} from "../../../../components/data-display/DataTable";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { BudgetRow } from "./budgetRows";
import BudgetMeter from "./BudgetMeter";

type BudgetColumn = DataTableColumn<BudgetRow, never, never>;

export interface BudgetTableProps {
  label: string;
  rows: BudgetRow[];
}

function budgetColumns(t: (key: string) => string): BudgetColumn[] {
  const header = (key: string) => t(`discovery_admin.artifacts.${key}`);
  return [
    {
      key: "resource",
      header: header("col_resource"),
      render: (row) => row.label,
    },
    {
      key: "usage",
      header: header("col_usage"),
      render: (row) => <BudgetMeter {...row} />,
    },
    {
      key: "status",
      header: header("col_status"),
      render: (row) =>
        row.exhausted ? (
          <Badge colorPalette="red" variant="subtle">
            {header("budget_exhausted")}
          </Badge>
        ) : null,
    },
  ];
}

/** Free-tier allowances as table rows: the resource, a read-only meter and its status. */
export default function BudgetTable({ label, rows }: BudgetTableProps) {
  const { t } = useLocale();

  return (
    <DataTable
      label={label}
      columns={budgetColumns(t)}
      rows={{ items: rows, getKey: (row) => row.key }}
    />
  );
}

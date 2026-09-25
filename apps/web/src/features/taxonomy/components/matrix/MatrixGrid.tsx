import { Table } from "@chakra-ui/react";

import type { MatrixAxisItem } from "../../types";
import MatrixColumnHeader from "./MatrixColumnHeader";
import MatrixCorner from "./MatrixCorner";
import MatrixRow from "./MatrixRow";

export interface MatrixGridProps {
  domains: MatrixAxisItem[];
  situations: MatrixAxisItem[];
  cellCounts: Map<string, number>;
  total: number;
}

/** Layout shell: situations as rows, domains as columns. */
export default function MatrixGrid({
  domains,
  situations,
  cellCounts,
  total,
}: MatrixGridProps) {
  return (
    <Table.Root size="sm" variant="outline">
      <Table.Header>
        <Table.Row>
          <Table.ColumnHeader>
            <MatrixCorner total={total} />
          </Table.ColumnHeader>
          {domains.map((domain) => (
            <Table.ColumnHeader key={domain.code} textAlign="center">
              <MatrixColumnHeader domain={domain} />
            </Table.ColumnHeader>
          ))}
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {situations.map((situation) => (
          <MatrixRow
            key={situation.code}
            situation={situation}
            domains={domains}
            cellCounts={cellCounts}
          />
        ))}
      </Table.Body>
    </Table.Root>
  );
}

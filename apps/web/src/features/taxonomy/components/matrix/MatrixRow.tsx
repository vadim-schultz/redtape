import { Table } from "@chakra-ui/react";

import type { MatrixAxisItem } from "../../types";
import { cellKey } from "../../utils/buildCellIndex";
import MatrixCell from "./MatrixCell";
import MatrixRowHeader from "./MatrixRowHeader";

export interface MatrixRowProps {
  situation: MatrixAxisItem;
  domains: MatrixAxisItem[];
  cellCounts: Map<string, number>;
}

export default function MatrixRow({
  situation,
  domains,
  cellCounts,
}: MatrixRowProps) {
  return (
    <Table.Row>
      <Table.Cell as="th" scope="row" textAlign="start">
        <MatrixRowHeader situation={situation} />
      </Table.Cell>
      {domains.map((domain) => (
        <Table.Cell key={domain.code}>
          <MatrixCell
            domain={domain}
            situation={situation}
            count={cellCounts.get(cellKey(domain.code, situation.code))}
          />
        </Table.Cell>
      ))}
    </Table.Row>
  );
}

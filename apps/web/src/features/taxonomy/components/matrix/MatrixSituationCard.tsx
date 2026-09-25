import { Card, HStack } from "@chakra-ui/react";

import type { MatrixAxisItem } from "../../types";
import { cellKey } from "../../utils/buildCellIndex";
import MatrixCell from "./MatrixCell";
import MatrixRowHeader from "./MatrixRowHeader";

export interface MatrixSituationCardProps {
  situation: MatrixAxisItem;
  domains: MatrixAxisItem[];
  cellCounts: Map<string, number>;
}

export default function MatrixSituationCard({
  situation,
  domains,
  cellCounts,
}: MatrixSituationCardProps) {
  const filled = domains.filter((d) =>
    cellCounts.has(cellKey(d.code, situation.code)),
  );

  return (
    <Card.Root
      as="section"
      aria-label={situation.name}
      bg="surface.base"
      shadow="card"
    >
      <Card.Body gap={3}>
        <MatrixRowHeader situation={situation} />
        <HStack wrap="wrap" gap={2}>
          {filled.map((domain) => (
            <HStack key={domain.code} gap={1}>
              <span>{domain.name}</span>
              <MatrixCell
                domain={domain}
                situation={situation}
                count={cellCounts.get(cellKey(domain.code, situation.code))}
              />
            </HStack>
          ))}
        </HStack>
      </Card.Body>
    </Card.Root>
  );
}

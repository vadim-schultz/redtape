import { Box } from "@chakra-ui/react";
import { useMemo } from "react";

import type { MatrixResponse, Term } from "../../types";
import { buildAxis } from "../../utils/buildAxis";
import { buildCellIndex } from "../../utils/buildCellIndex";
import MatrixDomainLinks from "./MatrixDomainLinks";
import MatrixGrid from "./MatrixGrid";
import MatrixSituationCards from "./MatrixSituationCards";

export interface MatrixViewProps {
  matrix: MatrixResponse;
  domains: Term[];
  situations: Term[];
}

/** Composes the two layouts; CSS picks which one shows. */
export default function MatrixView({
  matrix,
  domains,
  situations,
}: MatrixViewProps) {
  const cellCounts = useMemo(() => buildCellIndex(matrix.cells), [matrix]);
  const columns = buildAxis(domains, matrix.domains);
  const rows = buildAxis(situations, matrix.situations);

  return (
    <>
      <Box display={{ base: "none", md: "block" }}>
        <MatrixGrid
          domains={columns}
          situations={rows}
          cellCounts={cellCounts}
          total={matrix.total}
        />
      </Box>
      <Box display={{ base: "block", md: "none" }}>
        <MatrixDomainLinks domains={columns} />
        <MatrixSituationCards
          domains={columns}
          situations={rows}
          cellCounts={cellCounts}
        />
      </Box>
    </>
  );
}

import { HStack } from "@chakra-ui/react";

import type { MatrixAxisItem } from "../../types";
import MatrixColumnHeader from "./MatrixColumnHeader";

/** Phone-width stand-in for the column headers. */
export default function MatrixDomainLinks({
  domains,
}: {
  domains: MatrixAxisItem[];
}) {
  return (
    <HStack wrap="wrap" gap={2} mb={4}>
      {domains.map((domain) => (
        <MatrixColumnHeader key={domain.code} domain={domain} />
      ))}
    </HStack>
  );
}

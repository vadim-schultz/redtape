import { SimpleGrid, Stack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { DiscoveryBudget, DiscoveryCoverageResponse } from "../../types";
import { buildCoverageGroups } from "./coverageGroups";
import LlmCoverage from "./LlmCoverage";
import MetricGroupCard from "./MetricGroupCard";

export interface CoverageSummaryProps {
  coverage: DiscoveryCoverageResponse;
  /** Today's neuron budget, shown with the extraction outcomes when known. */
  neurons?: DiscoveryBudget;
  /** Independent sections below the summary, such as the budgets. */
  children?: ReactNode;
}

/**
 * The one coverage summary both admin routes render: grouped metric tables in
 * the shared shell. Slots after it keep their own queries and error states.
 */
export default function CoverageSummary({
  coverage,
  neurons,
  children,
}: CoverageSummaryProps) {
  const groups = buildCoverageGroups(coverage, useLocale());

  return (
    <Stack gap={4} align="stretch">
      <SimpleGrid columns={{ base: 1, xl: 2 }} gap={4} alignItems="start">
        {groups.map((group) => (
          <MetricGroupCard key={group.key} group={group} />
        ))}
        <LlmCoverage outcomes={coverage.llm_outcomes} neurons={neurons} />
      </SimpleGrid>
      {children}
    </Stack>
  );
}

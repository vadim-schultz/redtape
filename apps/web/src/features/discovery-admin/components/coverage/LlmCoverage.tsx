import { Stack } from "@chakra-ui/react";

import SectionCard from "../../../../components/data-display/SectionCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { DiscoveryBudget, DiscoveryLlmOutcomes } from "../../types";
import { budgetRowOf } from "./budgetRows";
import BudgetTable from "./BudgetTable";
import { llmGroup } from "./contentGroups";
import MetricTable from "./MetricTable";

export interface LlmCoverageProps {
  outcomes: DiscoveryLlmOutcomes;
  /** Today's neuron budget; absent while the budgets route has not answered. */
  neurons: DiscoveryBudget | undefined;
}

/** What the model runs produced, per outcome, and the neurons used of today's cap. */
export default function LlmCoverage({ outcomes, neurons }: LlmCoverageProps) {
  const context = useLocale();
  const group = llmGroup(outcomes, context);

  return (
    <SectionCard title={group.title}>
      <Stack gap={4}>
        <MetricTable group={group} />
        {neurons ? (
          <BudgetTable
            label={context.t("discovery_admin.artifacts.budget_neurons")}
            rows={[budgetRowOf(neurons, context)]}
          />
        ) : null}
      </Stack>
    </SectionCard>
  );
}

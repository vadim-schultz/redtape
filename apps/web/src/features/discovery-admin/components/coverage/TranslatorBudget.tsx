import { Text } from "@chakra-ui/react";

import SectionCard from "../../../../components/data-display/SectionCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { DiscoveryBudgetsResponse } from "../../types";
import { translatorBudgetOf } from "../../utils/translatorBudget";
import { budgetRowOf } from "./budgetRows";
import TranslatorBudgetMeter from "./TranslatorBudgetMeter";

export interface TranslatorBudgetProps {
  budgets: DiscoveryBudgetsResponse;
}

/** The Azure character meter of the monthly translation budget, or a note while its row is not configured. */
export default function TranslatorBudget({ budgets }: TranslatorBudgetProps) {
  const context = useLocale();
  const budget = translatorBudgetOf(budgets);

  return (
    <SectionCard
      title={context.t("discovery_admin.artifacts.translator_title")}
    >
      {budget ? (
        <TranslatorBudgetMeter row={budgetRowOf(budget, context)} />
      ) : (
        <Text fontSize="sm" color="muted">
          {context.t("discovery_admin.artifacts.translator_missing")}
        </Text>
      )}
    </SectionCard>
  );
}

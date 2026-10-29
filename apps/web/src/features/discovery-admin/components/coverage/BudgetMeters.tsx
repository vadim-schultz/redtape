import SectionCard from "../../../../components/data-display/SectionCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { DiscoveryBudgetsResponse } from "../../types";
import { budgetRowsOf } from "./budgetRows";
import BudgetTable from "./BudgetTable";

export interface BudgetMetersProps {
  budgets: DiscoveryBudgetsResponse;
}

/** Read-only free-tier allowances of the current periods and the stored bytes. */
export default function BudgetMeters({ budgets }: BudgetMetersProps) {
  const context = useLocale();
  if (budgets.items.length === 0) return null;
  const title = context.t("discovery_admin.artifacts.budgets_title");

  return (
    <SectionCard title={title}>
      <BudgetTable label={title} rows={budgetRowsOf(budgets, context)} />
    </SectionCard>
  );
}

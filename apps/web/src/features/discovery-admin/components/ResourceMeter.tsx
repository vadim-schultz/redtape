import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryBudget } from "../types";
import { formatNumber } from "../utils/formatNumber";
import { translateOrRaw } from "../utils/translateOrRaw";
import BudgetMeter from "./BudgetMeter";

/** The meter of one free-tier resource in its period: name, used of cap and what is left. */
export default function ResourceMeter({ budget }: { budget: DiscoveryBudget }) {
  const { locale, t } = useLocale();
  const name = translateOrRaw(
    t,
    `discovery_admin.artifacts.budget_${budget.resource}`,
    budget.resource,
  );
  const usage = t("discovery_admin.artifacts.budget_usage", {
    used: formatNumber(budget.used, locale),
    cap: formatNumber(budget.cap, locale),
    remaining: formatNumber(budget.remaining, locale),
  });

  return (
    <BudgetMeter
      label={`${name} · ${budget.period}`}
      used={budget.used}
      cap={budget.cap}
      usage={usage}
      exhausted={budget.exhausted}
    />
  );
}

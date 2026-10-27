import { Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryBudget, DiscoveryBudgetsResponse } from "../types";
import { formatBytes } from "../utils/formatBytes";
import { formatNumber } from "../utils/formatNumber";
import { translateOrRaw } from "../utils/translateOrRaw";
import BudgetMeter from "./BudgetMeter";

export interface BudgetMetersProps {
  budgets: DiscoveryBudgetsResponse;
}

function ResourceMeter({ budget }: { budget: DiscoveryBudget }) {
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

function StoredBytesMeter({ budgets }: BudgetMetersProps) {
  const { locale, t } = useLocale();
  const { stored_bytes: used, stored_bytes_cap: cap } = budgets;
  const usage = t("discovery_admin.artifacts.budget_usage", {
    used: formatBytes(used, locale),
    cap: formatBytes(cap, locale),
    remaining: formatBytes(Math.max(cap - used, 0), locale),
  });

  return (
    <BudgetMeter
      label={t("discovery_admin.artifacts.budget_stored_bytes")}
      used={used}
      cap={cap}
      usage={usage}
    />
  );
}

/** Read-only meters for the free-tier allowances of the current periods and the stored bytes. */
export default function BudgetMeters({ budgets }: BudgetMetersProps) {
  const { t } = useLocale();
  if (budgets.items.length === 0) return null;

  return (
    <Stack gap={3} align="stretch" maxW="28rem">
      <Text fontWeight="medium">
        {t("discovery_admin.artifacts.budgets_title")}
      </Text>
      {budgets.items.map((budget) => (
        <ResourceMeter key={budget.resource} budget={budget} />
      ))}
      <StoredBytesMeter budgets={budgets} />
    </Stack>
  );
}

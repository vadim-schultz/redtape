import type { DiscoveryBudget, DiscoveryBudgetsResponse } from "../../types";
import { formatBytes } from "../../utils/formatBytes";
import { formatNumber } from "../../utils/formatNumber";
import { generalBudgetsOf } from "../../utils/neuronBudget";
import { translateOrRaw } from "../../utils/translateOrRaw";
import type { MetricContext } from "./metricModel";

/** One free-tier allowance: what it is called, how much is used and what the text says. */
export interface BudgetRow {
  key: string;
  label: string;
  used: number;
  cap: number;
  usage: string;
  exhausted: boolean;
}

/** The row of one free-tier resource in its period; an unknown resource keeps its raw name. */
export function budgetRowOf(
  budget: DiscoveryBudget,
  { locale, t }: MetricContext,
): BudgetRow {
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
  return {
    key: budget.resource,
    label: `${name} · ${budget.period}`,
    used: budget.used,
    cap: budget.cap,
    usage,
    exhausted: budget.exhausted,
  };
}

function storedBytesRow(
  { stored_bytes: used, stored_bytes_cap: cap }: DiscoveryBudgetsResponse,
  { locale, t }: MetricContext,
): BudgetRow {
  const usage = t("discovery_admin.artifacts.budget_usage", {
    used: formatBytes(used, locale),
    cap: formatBytes(cap, locale),
    remaining: formatBytes(Math.max(cap - used, 0), locale),
  });
  return {
    key: "stored_bytes",
    label: t("discovery_admin.artifacts.budget_stored_bytes"),
    used,
    cap,
    usage,
    exhausted: false,
  };
}

/** The general budgets followed by the stored bytes; the neurons budget has its own table. */
export function budgetRowsOf(
  budgets: DiscoveryBudgetsResponse,
  context: MetricContext,
): BudgetRow[] {
  return [
    ...generalBudgetsOf(budgets).map((budget) => budgetRowOf(budget, context)),
    storedBytesRow(budgets, context),
  ];
}

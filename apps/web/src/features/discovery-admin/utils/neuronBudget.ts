import type { DiscoveryBudget, DiscoveryBudgetsResponse } from "../types";

const NEURONS = "neurons";

/** Today's AI neuron budget, which the extraction section shows instead of the general list. */
export function neuronBudgetOf(
  budgets: DiscoveryBudgetsResponse | undefined,
): DiscoveryBudget | undefined {
  return budgets?.items.find(({ resource }) => resource === NEURONS);
}

/** The budgets that belong to the general list: everything but the neurons. */
export function generalBudgetsOf(
  budgets: DiscoveryBudgetsResponse,
): DiscoveryBudget[] {
  return budgets.items.filter(({ resource }) => resource !== NEURONS);
}

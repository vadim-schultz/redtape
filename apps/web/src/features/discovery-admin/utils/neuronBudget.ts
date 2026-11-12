import type { DiscoveryBudget, DiscoveryBudgetsResponse } from "../types";

const NEURONS = "neurons";
const AZURE_TRANSLATOR_CHARS = "azure_translator_chars";

/** Today's AI neuron budget, which the extraction section shows instead of the general list. */
export function neuronBudgetOf(
  budgets: DiscoveryBudgetsResponse | undefined,
): DiscoveryBudget | undefined {
  return budgets?.items.find(({ resource }) => resource === NEURONS);
}

/** The budgets that belong to the general list: everything but the neurons and the Azure characters. */
export function generalBudgetsOf(
  budgets: DiscoveryBudgetsResponse,
): DiscoveryBudget[] {
  return budgets.items.filter(
    ({ resource }) =>
      resource !== NEURONS && resource !== AZURE_TRANSLATOR_CHARS,
  );
}

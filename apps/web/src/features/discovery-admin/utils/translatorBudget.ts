import type { DiscoveryBudget, DiscoveryBudgetsResponse } from "../types";

const AZURE_TRANSLATOR_CHARS = "azure_translator_chars";

/** Today's Azure character budget, which the Translator section shows apart from the general list. */
export function translatorBudgetOf(
  budgets: DiscoveryBudgetsResponse | undefined,
): DiscoveryBudget | undefined {
  return budgets?.items.find(
    ({ resource }) => resource === AZURE_TRANSLATOR_CHARS,
  );
}

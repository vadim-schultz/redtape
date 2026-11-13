import type { DiscoveryBudget, DiscoveryBudgetsResponse } from "../types";
import { AZURE_TRANSLATOR_CHARS, budgetsWhere } from "./budgetResources";

/** Today's Azure character budget, which the Translator section shows apart from the general list. */
export function translatorBudgetOf(
  budgets: DiscoveryBudgetsResponse | undefined,
): DiscoveryBudget | undefined {
  return budgetsWhere(
    budgets,
    (resource) => resource === AZURE_TRANSLATOR_CHARS,
  )[0];
}

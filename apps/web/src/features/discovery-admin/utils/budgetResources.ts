import type { DiscoveryBudget, DiscoveryBudgetsResponse } from "../types";

/** The resource the extraction section shows as its own meter. */
export const NEURONS = "neurons";
/** The resource the Translator section shows as its own meter. */
export const AZURE_TRANSLATOR_CHARS = "azure_translator_chars";

/** The budgets whose resource satisfies `keep`, in the order the response lists them. */
export function budgetsWhere(
  budgets: DiscoveryBudgetsResponse | undefined,
  keep: (resource: string) => boolean,
): DiscoveryBudget[] {
  return budgets?.items.filter(({ resource }) => keep(resource)) ?? [];
}

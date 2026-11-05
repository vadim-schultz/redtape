import type { DocumentFilters } from "../hooks/useDocumentFilters";

/** Return whether at least one category narrows the list. */
export function hasSelectedChips(
  filters: Pick<DocumentFilters, "categories">,
): boolean {
  return filters.categories.length > 0;
}

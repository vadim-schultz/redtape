import type { DocumentFilters } from "../hooks/useDocumentFilters";

/** True while at least one domain or situation chip narrows the list. */
export function hasSelectedChips(
  filters: Pick<DocumentFilters, "domains" | "situations">,
): boolean {
  return filters.domains.length + filters.situations.length > 0;
}

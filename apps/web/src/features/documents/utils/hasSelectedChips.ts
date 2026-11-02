import type { DocumentFilters } from "../hooks/useDocumentFilters";

/** True while at least one domain, life-area or situation chip narrows the list. */
export function hasSelectedChips(
  filters: Pick<DocumentFilters, "domains" | "groups" | "situations">,
): boolean {
  const { domains, groups, situations } = filters;
  return domains.length + groups.length + situations.length > 0;
}

import type { DocumentFilters } from "../hooks/useDocumentFilters";

/** True while at least one canonical or legacy filter narrows the list. */
export function hasSelectedChips(
  filters: Pick<DocumentFilters, "categories" | "legacy">,
): boolean {
  const { categories, legacy } = filters;
  return (
    categories.length +
    legacy.domain.length +
    legacy.group.length +
    legacy.situation.length >
    0
  );
}

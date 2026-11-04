import { useCategoryTreeQuery } from "../../taxonomy/hooks/useCategoryTreeQuery";
import type { CategoryNode } from "../../taxonomy/types";

export interface FilterTaxonomy {
  categories: CategoryNode[];
  isError: boolean;
  onRetry: () => void;
}

/** Canonical category tree for the filter chips, with one retry action. */
export function useFilterTaxonomy(): FilterTaxonomy {
  const categories = useCategoryTreeQuery();

  return {
    categories: categories.data ?? [],
    isError: categories.isError,
    onRetry: () => void categories.refetch(),
  };
}

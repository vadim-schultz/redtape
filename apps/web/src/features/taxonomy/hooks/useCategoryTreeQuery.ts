import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchCategoryTree } from "../services/taxonomyApi";
import type { CategoryNode } from "../types";
import { TAXONOMY_STALE_TIME_MS } from "../utils/staleTime";

/** Load the localized canonical category tree for public browsing. */
export function useCategoryTreeQuery() {
  const { locale } = useLocale();

  return useApiQuery<CategoryNode[]>(
    queryKeys.taxonomy.categories(locale),
    () => fetchCategoryTree(locale),
    { staleTime: TAXONOMY_STALE_TIME_MS },
  );
}

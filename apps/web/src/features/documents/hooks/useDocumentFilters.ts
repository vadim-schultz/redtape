import { useSearchParams } from "react-router-dom";

import type { CategoryNode } from "../../taxonomy/types";
import {
  FILTER_PARAMS,
  readValidCategoryCodes,
  withToggledCategory,
  withoutParams,
} from "../utils/filterParams";

export interface DocumentFilters {
  categories: string[];
  toggleCategory: (code: string, parentCode?: string | null) => void;
  /** Drops the chips and returns to the first page; search and sort stay. */
  clear: () => void;
  /** Drops the chips and the search term and returns to the first page; sort stays. */
  clearAll: () => void;
}

/** Read canonical category state from the URL. */
export function useDocumentFilters(
  taxonomy: CategoryNode[] = [],
): DocumentFilters {
  const [params, setParams] = useSearchParams();

  return {
    categories: readValidCategoryCodes(params, taxonomy),
    toggleCategory: (code, parentCode) =>
      setParams((prev) => withToggledCategory(prev, code, parentCode)),
    clear: () => setParams((prev) => withoutParams(prev, [...FILTER_PARAMS])),
    clearAll: () =>
      setParams((prev) => withoutParams(prev, [...FILTER_PARAMS, "q"])),
  };
}

import { useCategoryNames } from "../../taxonomy/hooks/useCategoryNames";

/** Display names of the suggested categories, by code; empty while loading or after a failure. */
export function useTagNames() {
  return { categoryNames: useCategoryNames() };
}

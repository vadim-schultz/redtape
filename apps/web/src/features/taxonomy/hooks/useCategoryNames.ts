import { categoryNamesByCode } from "../utils/categoryNames";
import { useCategoryTreeQuery } from "./useCategoryTreeQuery";

/** Localized names of the canonical category tree, by code; empty while loading or after a failure. */
export function useCategoryNames(): Record<string, string> {
  const tree = useCategoryTreeQuery();

  return categoryNamesByCode(tree.data);
}

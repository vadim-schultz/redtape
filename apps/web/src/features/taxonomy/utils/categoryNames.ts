import { flattenCategories } from "../../../utils/categoryTree";
import type { CategoryNode } from "../types";

/** Localized names of every canonical category in the tree, by code; empty for no tree. */
export function categoryNamesByCode(
  nodes: CategoryNode[] = [],
): Record<string, string> {
  return Object.fromEntries(
    flattenCategories(nodes).map((node) => [node.code, node.name]),
  );
}

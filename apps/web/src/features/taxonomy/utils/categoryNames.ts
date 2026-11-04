import type { CategoryNode } from "../types";

function flattenCategories(nodes: CategoryNode[]): CategoryNode[] {
  if (!Array.isArray(nodes)) return [];
  return nodes.flatMap((node) => [node, ...flattenCategories(node.children)]);
}

/** Localized names of every canonical category in the tree, by code; empty for no tree. */
export function categoryNamesByCode(
  nodes: CategoryNode[] = [],
): Record<string, string> {
  return Object.fromEntries(
    flattenCategories(nodes).map((node) => [node.code, node.name]),
  );
}

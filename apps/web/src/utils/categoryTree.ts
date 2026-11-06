/** Every node of a tree whose nodes list their `children`, depth first; a value that is not a list yields none. */
export function flattenCategories<T extends { children: T[] }>(
  nodes: T[],
): T[] {
  if (!Array.isArray(nodes)) return [];
  return nodes.flatMap((node) => [node, ...flattenCategories(node.children)]);
}

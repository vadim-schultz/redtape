import type { GraphEdge } from "./graphTypes";

interface Keyed {
  id: string;
  key: number;
  index: number;
}

/** The ids of each layer, in input order, before any ordering. */
function groupByLayer(
  ids: readonly string[],
  layer: ReadonlyMap<string, number>,
): string[][] {
  const depth = ids.reduce((max, id) => Math.max(max, layer.get(id) ?? 0), -1);
  const groups: string[][] = Array.from({ length: depth + 1 }, () => []);
  for (const id of ids) groups[layer.get(id) ?? 0].push(id);
  return groups;
}

/**
 * The barycentre of a stage: the mean position of the stages one layer up that feed it.
 * A stage in layer 0 has no such feed and keeps its input order, so it gets 0.
 */
function barycentre(
  id: string,
  edges: readonly GraphEdge[],
  layer: ReadonlyMap<string, number>,
  position: ReadonlyMap<string, number>,
): number {
  const above = (layer.get(id) ?? 0) - 1;
  const feeds = edges
    .filter((edge) => edge.to === id && layer.get(edge.from) === above)
    .map((edge) => position.get(edge.from) ?? 0);
  if (feeds.length === 0) return 0;
  return feeds.reduce((sum, value) => sum + value, 0) / feeds.length;
}

/** Sort one layer by barycentre, then by input order, so equal keys never move. */
function orderGroup(
  group: readonly string[],
  inputIndex: ReadonlyMap<string, number>,
  keyOf: (id: string) => number,
): string[] {
  const keyed: Keyed[] = group.map((id) => ({
    id,
    key: keyOf(id),
    index: inputIndex.get(id) ?? 0,
  }));
  keyed.sort((a, b) => a.key - b.key || a.index - b.index);
  return keyed.map(({ id }) => id);
}

/**
 * The stages of each layer in their drawn order. Layers are processed from the top down, so each layer is ordered
 * against positions that are already fixed. The result depends only on the input order, so it is deterministic.
 */
export function orderLayers(
  ids: readonly string[],
  edges: readonly GraphEdge[],
  layer: ReadonlyMap<string, number>,
): string[][] {
  const inputIndex = new Map(ids.map((id, index) => [id, index]));
  const position = new Map<string, number>();
  return groupByLayer(ids, layer).map((group) => {
    const ordered = orderGroup(group, inputIndex, (id) =>
      barycentre(id, edges, layer, position),
    );
    ordered.forEach((id, index) => position.set(id, index));
    return ordered;
  });
}

import type { GraphEdge } from "./graphTypes";

/** The depth found so far for each stage, and how many edges still point into each stage. */
interface LayerState {
  layer: Map<string, number>;
  waiting: Map<string, number>;
}

/** Reject an edge end that is not a stage of the graph. */
function assertKnownEnd(known: ReadonlySet<string>, id: string): void {
  if (!known.has(id))
    throw new Error(`The flow graph has an edge to an unknown stage ${id}`);
}

/** Reject an id that repeats and an edge that names a stage which is not in the graph. */
function assertKnown(
  ids: readonly string[],
  edges: readonly GraphEdge[],
): void {
  const known = new Set(ids);
  if (known.size !== ids.length)
    throw new Error("The flow graph repeats a stage id");
  for (const edge of edges) {
    assertKnownEnd(known, edge.from);
    assertKnownEnd(known, edge.to);
  }
}

/** How many edges still point into each stage: the stages with none are the sources. */
function waitingCounts(
  ids: readonly string[],
  edges: readonly GraphEdge[],
): Map<string, number> {
  const waiting = new Map(ids.map((id) => [id, 0]));
  for (const { to } of edges) waiting.set(to, (waiting.get(to) ?? 0) + 1);
  return waiting;
}

/** Lift `target` to at least `depth` and count one edge as settled; a stage whose last edge settles is ready. */
function relax(target: string, depth: number, state: LayerState): string[] {
  state.layer.set(target, Math.max(state.layer.get(target) ?? 0, depth));
  const remaining = (state.waiting.get(target) ?? 0) - 1;
  state.waiting.set(target, remaining);
  return remaining === 0 ? [target] : [];
}

/** Relax every edge out of `id`, and return the stages that became ready. */
function settle(
  id: string,
  edges: readonly GraphEdge[],
  state: LayerState,
): string[] {
  const depth = (state.layer.get(id) ?? 0) + 1;
  return edges
    .filter((edge) => edge.from === id)
    .flatMap((edge) => relax(edge.to, depth, state));
}

/** The ids that never became ready: a cycle runs through them. */
function stuckIds(
  ids: readonly string[],
  settled: readonly string[],
): string[] {
  const done = new Set(settled);
  return ids.filter((id) => !done.has(id));
}

/**
 * The layer of each stage: the length of the longest path that ends at it, so every edge points to a later layer.
 * Kahn's order settles the stages; a stage left unsettled means a cycle.
 */
export function assignLayers(
  ids: readonly string[],
  edges: readonly GraphEdge[],
): Map<string, number> {
  assertKnown(ids, edges);
  const state: LayerState = {
    layer: new Map(ids.map((id) => [id, 0])),
    waiting: waitingCounts(ids, edges),
  };
  const ready = ids.filter((id) => state.waiting.get(id) === 0);
  for (let next = 0; next < ready.length; next += 1) {
    ready.push(...settle(ready[next], edges, state));
  }
  const stuck = stuckIds(ids, ready);
  if (stuck.length > 0)
    throw new Error(`The flow graph has a cycle through ${stuck.join(", ")}`);
  return state.layer;
}

import type {
  GraphEdge,
  GraphGeometry,
  PlacedEdge,
  PlacedNode,
} from "./graphTypes";

/** A cubic curve from the right side of the source box to the left side of the target box. */
export function edgePath(
  source: PlacedNode,
  target: PlacedNode,
  g: GraphGeometry,
): string {
  const x1 = source.x + g.nodeWidth;
  const y1 = source.y + g.nodeHeight / 2;
  const x2 = target.x;
  const y2 = target.y + g.nodeHeight / 2;
  const bend = g.columnGap / 2;
  return `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`;
}

/** Look up both ends of an edge; `assignLayers` has already checked that they exist. */
export function placeEdge(
  edge: GraphEdge,
  byId: ReadonlyMap<string, PlacedNode>,
  g: GraphGeometry,
): PlacedEdge {
  const source = byId.get(edge.from);
  const target = byId.get(edge.to);
  if (!source || !target)
    throw new Error(
      `The flow graph has an edge to an unknown stage ${edge.to}`,
    );
  return {
    from: edge.from,
    to: edge.to,
    dashed: edge.dashed ?? false,
    d: edgePath(source, target, g),
  };
}

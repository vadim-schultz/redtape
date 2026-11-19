import { placeEdge } from "./edgeGeometry";
import { assignLayers } from "./layerGraph";
import { canvasSize, placeNodes, tallestColumn } from "./graphPlacement";
import { orderLayers } from "./orderLayers";
import type {
  GraphEdge,
  GraphGeometry,
  GraphLayout,
  GraphNode,
} from "./graphTypes";

export type {
  GraphEdge,
  GraphGeometry,
  GraphLayout,
  GraphNode,
  PlacedEdge,
  PlacedNode,
} from "./graphTypes";

/** Default box and gap sizes, in pixels. A renderer sizes its stage content to `nodeWidth` by `nodeHeight`. */
const GRAPH_GEOMETRY: GraphGeometry = {
  nodeWidth: 216,
  nodeHeight: 200,
  columnGap: 48,
  rowGap: 16,
  padding: 8,
};

/**
 * Where every stage and edge of a directed graph goes. Pure: no DOM, no measuring and no React.
 * Rejects a cycle and an edge to a stage that is not in `nodes`. The output depends only on the input.
 */
export function layoutGraph(
  nodes: readonly GraphNode[],
  edges: readonly GraphEdge[],
): GraphLayout {
  const geometry = GRAPH_GEOMETRY;
  const ids = nodes.map((node) => node.id);
  const rows = orderLayers(ids, edges, assignLayers(ids, edges));
  const placed = placeNodes(rows, geometry);
  const byId = new Map(placed.map((node) => [node.id, node]));
  return {
    ...canvasSize(rows.length, tallestColumn(rows, geometry), geometry),
    nodes: placed,
    edges: edges.map((edge) => placeEdge(edge, byId, geometry)),
    geometry,
  };
}

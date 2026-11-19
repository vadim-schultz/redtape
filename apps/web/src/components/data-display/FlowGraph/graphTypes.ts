/** A stage of the graph. Its id is what the edges and the render prop refer to. */
export interface GraphNode {
  readonly id: string;
}

/** A directed edge from one stage to the stage it feeds. `dashed` draws it as a dashed line. */
export interface GraphEdge {
  readonly from: string;
  readonly to: string;
  readonly dashed?: boolean;
}

/** The size of a stage box and the gaps between boxes, in pixels. */
export interface GraphGeometry {
  readonly nodeWidth: number;
  readonly nodeHeight: number;
  readonly columnGap: number;
  readonly rowGap: number;
  readonly padding: number;
}

/** A stage with its layer (column), its place within the layer and its top-left corner. */
export interface PlacedNode {
  readonly id: string;
  readonly layer: number;
  readonly order: number;
  readonly x: number;
  readonly y: number;
}

/** An edge with its SVG path, from the right edge of its source box to the left edge of its target. */
export interface PlacedEdge {
  readonly from: string;
  readonly to: string;
  readonly dashed: boolean;
  readonly d: string;
}

/** Everything a renderer needs: the canvas size, the boxes in topological order and the edges. */
export interface GraphLayout {
  readonly width: number;
  readonly height: number;
  readonly nodes: PlacedNode[];
  readonly edges: PlacedEdge[];
  readonly geometry: GraphGeometry;
}

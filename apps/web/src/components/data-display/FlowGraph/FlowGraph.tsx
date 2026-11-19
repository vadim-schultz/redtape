import { Box } from "@chakra-ui/react";
import type { ReactNode } from "react";

import FlowEdges from "./FlowEdges";
import type { GraphGeometry, GraphLayout, PlacedNode } from "./graphTypes";

export interface FlowGraphProps {
  /** Positions from `layoutGraph`; the graph draws them and does no layout itself. */
  layout: GraphLayout;
  /** The content of one stage box, given the stage id. */
  renderNode: (id: string) => ReactNode;
  /** The accessible name of the graph. */
  label: string;
}

interface PlacedBoxProps {
  node: PlacedNode;
  geometry: GraphGeometry;
  children: ReactNode;
}

/** One stage box at its layout position, sized to the layout's geometry. */
function PlacedBox({ node, geometry, children }: PlacedBoxProps) {
  const style = {
    left: node.x,
    top: node.y,
    width: geometry.nodeWidth,
    height: geometry.nodeHeight,
  };

  return (
    <Box position="absolute" style={style} data-graph-node={node.id}>
      {children}
    </Box>
  );
}

/** The stage boxes at their positions, with the arrows drawn behind them, in a box that scrolls sideways when narrow. */
export default function FlowGraph({
  layout,
  renderNode,
  label,
}: FlowGraphProps) {
  return (
    <Box role="group" aria-label={label} overflowX="auto" maxWidth="100%">
      <Box
        position="relative"
        style={{ width: layout.width, height: layout.height }}
      >
        <FlowEdges layout={layout} />
        {layout.nodes.map((node) => (
          <PlacedBox key={node.id} node={node} geometry={layout.geometry}>
            {renderNode(node.id)}
          </PlacedBox>
        ))}
      </Box>
    </Box>
  );
}

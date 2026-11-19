import { chakra } from "@chakra-ui/react";
import { useId } from "react";

import type { GraphLayout } from "./graphTypes";

export interface FlowEdgesProps {
  layout: Pick<GraphLayout, "width" | "height" | "edges">;
}

/** Colours come from semantic tokens, the same ones the candidate FlowPaths uses, so light and dark need no branches. */
const EDGE_STYLES = {
  "& .graph-edge": {
    fill: "none",
    stroke: "border.emphasized",
    strokeWidth: "2px",
  },
  "& .graph-arrowhead": { fill: "fg.muted" },
};

/** The arrow tip, shared by every edge of one graph. */
function Arrowhead({ id }: { id: string }) {
  return (
    <marker
      id={id}
      viewBox="0 0 6 6"
      refX="6"
      refY="3"
      markerWidth="6"
      markerHeight="6"
      orient="auto"
    >
      <path className="graph-arrowhead" d="M 0 0 L 6 3 L 0 6 z" />
    </marker>
  );
}

/** Every edge as an arrow behind the stage boxes. The boxes carry the information, so the SVG is hidden from assistive tech. */
export default function FlowEdges({ layout }: FlowEdgesProps) {
  const markerId = `graph-arrow-${useId().replace(/\W/g, "")}`;
  const { width, height, edges } = layout;

  return (
    <chakra.svg
      aria-hidden="true"
      focusable="false"
      htmlWidth={width}
      htmlHeight={height}
      viewBox={`0 0 ${width} ${height}`}
      position="absolute"
      top="0"
      left="0"
      css={EDGE_STYLES}
    >
      <defs>
        <Arrowhead id={markerId} />
      </defs>
      {edges.map((edge) => (
        <path
          key={`${edge.from}->${edge.to}`}
          className="graph-edge"
          d={edge.d}
          markerEnd={`url(#${markerId})`}
          strokeDasharray={edge.dashed ? "6 4" : undefined}
        />
      ))}
    </chakra.svg>
  );
}

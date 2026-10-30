import { chakra } from "@chakra-ui/react";
import { useId } from "react";

import type { FlowLayout } from "../../utils/layoutFlow";

export interface FlowPathsProps {
  layout: Pick<FlowLayout, "width" | "height" | "paths">;
}

/** Colours come from semantic tokens, so light and dark need no branches. */
const EDGE_STYLES = {
  "& .flow-edge": {
    fill: "none",
    stroke: "border.emphasized",
    strokeWidth: "2px",
  },
  "& .flow-arrowhead": { fill: "fg.muted" },
};

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
      <path className="flow-arrowhead" d="M 0 0 L 6 3 L 0 6 z" />
    </marker>
  );
}

/** The decorative arrows behind the cards; the cards carry all the information. */
export default function FlowPaths({ layout }: FlowPathsProps) {
  const markerId = `flow-arrow-${useId().replace(/\W/g, "")}`;
  const { width, height, paths } = layout;

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
      {paths.map(({ from, index, d }) => (
        <path
          key={`${from}-${index}`}
          className="flow-edge"
          d={d}
          markerEnd={`url(#${markerId})`}
        />
      ))}
    </chakra.svg>
  );
}

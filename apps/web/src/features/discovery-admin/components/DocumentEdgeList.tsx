import { Stack, Text } from "@chakra-ui/react";

import type { DiscoveryCandidateEdge } from "../types";
import DocumentEdgeItem, { type EdgeEnd } from "./DocumentEdgeItem";

/** A titled list of edges; renders nothing when there are none. */
export default function DocumentEdgeList({
  title,
  edges,
  end,
}: {
  title: string;
  edges: DiscoveryCandidateEdge[];
  end: EdgeEnd;
}) {
  if (edges.length === 0) return null;

  return (
    <Stack gap={1} align="stretch">
      <Text fontSize="sm" color="muted">
        {title}
      </Text>
      <Stack as="ul" aria-label={title} gap={1} listStyleType="none" ps={0}>
        {edges.map((edge) => (
          <DocumentEdgeItem key={edge.id} edge={edge} end={end} />
        ))}
      </Stack>
    </Stack>
  );
}

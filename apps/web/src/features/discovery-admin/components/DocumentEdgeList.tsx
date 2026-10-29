import { Stack, Text } from "@chakra-ui/react";

import { DataTable } from "../../../components/data-display/DataTable";
import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCandidateEdge } from "../types";
import { edgeColumns, type EdgeEnd } from "./columns/edgeColumns";

/** A titled edge table; renders nothing when there are none. */
export default function DocumentEdgeList({
  title,
  edges,
  end,
}: {
  title: string;
  edges: DiscoveryCandidateEdge[];
  end: EdgeEnd;
}) {
  const locale = useLocale();
  if (edges.length === 0) return null;

  return (
    <Stack gap={1} align="stretch">
      <Text textStyle="caption" color="muted">
        {title}
      </Text>
      <DataTable
        label={title}
        columns={edgeColumns(locale, end)}
        rows={{ items: edges, getKey: (edge) => edge.id }}
      />
    </Stack>
  );
}

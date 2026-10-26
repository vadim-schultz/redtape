import { Box, Text } from "@chakra-ui/react";
import { LuFileText } from "react-icons/lu";

import NamespacedEmptyState from "../../../components/feedback/NamespacedEmptyState";
import QueryError from "../../../components/feedback/QueryError";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useCountLabel } from "../../../components/feedback/useCountLabel";
import type { DiscoveryCandidateListResponse } from "../types";

import DiscoveryTasksSkeleton from "./DiscoveryTasksSkeleton";
import DiscoveryDocumentsTable from "./DiscoveryDocumentsTable";
import PaginationControl from "./PaginationControl";

export interface DiscoveryDocumentsQueryStatusProps {
  status: QueryStatus;
  page: DiscoveryCandidateListResponse | undefined;
  limit: number;
  onOffsetChange: (offset: number) => void;
}

const NAMESPACE = "discovery_admin.documents";

/** Loading, error, empty or ready state of the documents list. */
export default function DiscoveryDocumentsQueryStatus({
  status,
  page,
  limit,
  onOffsetChange,
}: DiscoveryDocumentsQueryStatusProps) {
  const countLabel = useCountLabel(NAMESPACE);

  if (status.isError) return <QueryError onRetry={status.onRetry} />;
  if (!page) return <DiscoveryTasksSkeleton />;
  if (page.items.length === 0)
    return <NamespacedEmptyState namespace={NAMESPACE} icon={LuFileText} />;

  return (
    <>
      <Text mb={2} color="muted" fontSize="sm">
        {countLabel(page.total)}
      </Text>
      <Box
        aria-busy={status.isRefreshing}
        opacity={status.isRefreshing ? 0.6 : 1}
        transition="opacity 0.2s"
      >
        <DiscoveryDocumentsTable candidates={page.items} />
      </Box>
      <PaginationControl
        offset={page.offset}
        limit={limit}
        total={page.total}
        onOffsetChange={onOffsetChange}
      />
    </>
  );
}

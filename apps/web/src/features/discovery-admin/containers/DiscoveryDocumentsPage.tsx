import { VStack } from "@chakra-ui/react";

import { toQueryStatus } from "../../../components/feedback/queryStatus";
import DiscoveryDocumentFilters from "../components/DiscoveryDocumentFilters";
import DiscoveryDocumentsQueryStatus from "../components/DiscoveryDocumentsQueryStatus";
import { useDiscoveryCandidatesQuery } from "../hooks/useDiscoveryCandidatesQuery";
import { useDiscoveryDocumentFilters } from "../hooks/useDiscoveryDocumentFilters";

/** Admin document candidates at ``/admin/discovery/documents``. */
export default function DiscoveryDocumentsPage() {
  const filters = useDiscoveryDocumentFilters();
  const candidatesQuery = useDiscoveryCandidatesQuery(filters);

  return (
    <VStack align="stretch" gap={4}>
      <DiscoveryDocumentFilters filters={filters} />
      <DiscoveryDocumentsQueryStatus
        status={toQueryStatus(candidatesQuery)}
        page={candidatesQuery.data}
        limit={filters.limit}
        onOffsetChange={filters.setOffset}
      />
    </VStack>
  );
}

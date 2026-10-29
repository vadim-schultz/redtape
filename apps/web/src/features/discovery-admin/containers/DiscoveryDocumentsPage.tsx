import { VStack } from "@chakra-ui/react";

import { toQueryStatus } from "../../../components/feedback/queryStatus";
import DiscoveryDocumentFilters from "../components/DiscoveryDocumentFilters";
import DiscoveryDocumentsTable from "../components/DiscoveryDocumentsTable";
import { useCandidateListState } from "../hooks/useCandidateListState";
import { useDiscoveryCandidatesQuery } from "../hooks/useDiscoveryCandidatesQuery";

/** Admin document candidates at ``/admin/discovery/documents``. */
export default function DiscoveryDocumentsPage() {
  const list = useCandidateListState();
  const candidatesQuery = useDiscoveryCandidatesQuery(list.state);

  return (
    <VStack align="stretch" gap={4}>
      <DiscoveryDocumentFilters list={list} />
      <DiscoveryDocumentsTable
        page={candidatesQuery.data}
        status={toQueryStatus(candidatesQuery)}
        list={list}
      />
    </VStack>
  );
}

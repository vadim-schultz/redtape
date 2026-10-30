import { toQueryStatus } from "../../../components/feedback/queryStatus";
import DiscoveryDocumentsTable from "../components/DiscoveryDocumentsTable";
import { useCandidateListState } from "../hooks/useCandidateListState";
import { useDiscoveryCandidatesQuery } from "../hooks/useDiscoveryCandidatesQuery";

/** Admin document candidates at ``/admin/discovery/documents``. */
export default function DiscoveryDocumentsPage() {
  const list = useCandidateListState();
  const candidatesQuery = useDiscoveryCandidatesQuery(list.state);

  return (
    <DiscoveryDocumentsTable
      page={candidatesQuery.data}
      status={toQueryStatus(candidatesQuery)}
      list={list}
    />
  );
}

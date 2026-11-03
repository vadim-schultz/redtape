import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { useListQueryState } from "../../../hooks/useListQueryState";
import DiscoveryDocumentsTable from "../components/DiscoveryDocumentsTable";
import { useDiscoveryCandidatesQuery } from "../hooks/useDiscoveryCandidatesQuery";
import { CANDIDATE_LIST_SPEC } from "../services/candidateListQuery";

/** Admin document candidates at ``/admin/discovery/documents``. */
export default function DiscoveryDocumentsPage() {
  const list = useListQueryState(CANDIDATE_LIST_SPEC);
  const candidatesQuery = useDiscoveryCandidatesQuery(list.state);

  return (
    <DiscoveryDocumentsTable
      page={candidatesQuery.data}
      status={toQueryStatus(candidatesQuery)}
      list={list}
    />
  );
}

import QueryError from "../../../components/feedback/QueryError";
import { FlowView } from "../components/FlowView";
import DiscoveryAdminLoading from "../components/DiscoveryAdminLoading";
import { useDiscoveryFlowQuery } from "../hooks/useDiscoveryFlowQuery";

/** The pipeline flow at ``/admin/discovery/flow``. A refetch that fails keeps the last picture on screen. */
export default function DiscoveryFlowPage() {
  const flowQuery = useDiscoveryFlowQuery();

  if (flowQuery.data)
    return <FlowView flow={flowQuery.data} readAt={flowQuery.dataUpdatedAt} />;
  if (flowQuery.isError) {
    return <QueryError onRetry={() => void flowQuery.refetch()} />;
  }
  return <DiscoveryAdminLoading />;
}

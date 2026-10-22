import QueryError from "../../../components/feedback/QueryError";
import CoverageChips from "../components/CoverageChips";
import DiscoveryAdminLoading from "../components/DiscoveryAdminLoading";
import { useDiscoveryCoverageQuery } from "../hooks/useDiscoveryCoverageQuery";

/** Coverage summary at ``/admin/discovery/coverage``. */
export default function DiscoveryCoveragePage() {
  const coverageQuery = useDiscoveryCoverageQuery();

  if (coverageQuery.isLoading) {
    return <DiscoveryAdminLoading />;
  }

  if (coverageQuery.isError || !coverageQuery.data) {
    return <QueryError onRetry={() => void coverageQuery.refetch()} />;
  }

  return <CoverageChips coverage={coverageQuery.data} />;
}

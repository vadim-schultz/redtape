import DiscoveryTasksView from "../components/DiscoveryTasksView";
import { useDiscoveryTaskFilters } from "../hooks/useDiscoveryTaskFilters";
import { useDiscoveryTasksQuery } from "../hooks/useDiscoveryTasksQuery";

/** Admin crawler queue at ``/admin/discovery/tasks``. */
export default function DiscoveryTasksPage() {
  const filters = useDiscoveryTaskFilters();
  const tasksQuery = useDiscoveryTasksQuery(filters);

  return (
    <DiscoveryTasksView
      filters={filters}
      tasks={tasksQuery.data?.items}
      isLoading={tasksQuery.isLoading}
      isRefreshing={tasksQuery.isFetching && !tasksQuery.isLoading}
      isError={tasksQuery.isError}
      error={tasksQuery.error}
      onRetry={() => void tasksQuery.refetch()}
    />
  );
}

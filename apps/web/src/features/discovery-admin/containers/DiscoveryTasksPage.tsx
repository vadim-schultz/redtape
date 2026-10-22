import { toQueryStatus } from "../../../components/feedback/queryStatus";
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
      status={toQueryStatus(tasksQuery)}
    />
  );
}

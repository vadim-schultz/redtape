import { toQueryStatus } from "../../../components/feedback/queryStatus";
import DiscoveryTasksView from "../components/DiscoveryTasksView";
import { useDiscoveryTasksQuery } from "../hooks/useDiscoveryTasksQuery";
import { useTaskListState } from "../hooks/useTaskListState";

/** Admin crawler queue at ``/admin/discovery/tasks``. */
export default function DiscoveryTasksPage() {
  const list = useTaskListState();
  const tasksQuery = useDiscoveryTasksQuery(list.state);

  return (
    <DiscoveryTasksView
      list={list}
      page={tasksQuery.data}
      status={toQueryStatus(tasksQuery)}
    />
  );
}

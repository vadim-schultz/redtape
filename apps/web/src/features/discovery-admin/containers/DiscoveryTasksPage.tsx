import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { useListQueryState } from "../../../hooks/useListQueryState";
import DiscoveryTasksView from "../components/DiscoveryTasksView";
import { useDiscoveryTasksQuery } from "../hooks/useDiscoveryTasksQuery";
import { TASK_LIST_SPEC } from "../services/taskListQuery";

/** Admin crawler queue at ``/admin/discovery/tasks``. */
export default function DiscoveryTasksPage() {
  const list = useListQueryState(TASK_LIST_SPEC);
  const tasksQuery = useDiscoveryTasksQuery(list.state);

  return (
    <DiscoveryTasksView
      list={list}
      page={tasksQuery.data}
      status={toQueryStatus(tasksQuery)}
    />
  );
}

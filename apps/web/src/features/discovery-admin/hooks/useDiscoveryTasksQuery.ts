import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { listDiscoveryTasks } from "../services/discoveryAdminApi";
import type { TaskListQuery } from "../services/taskListQuery";
import type { DiscoveryTaskListResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** One page of the crawler queue for the typed query state. */
export function useDiscoveryTasksQuery(query: TaskListQuery) {
  return useAdminQuery<DiscoveryTaskListResponse>(
    (locale) => queryKeys.discoveryAdmin.tasks(query, locale),
    (auth) => listDiscoveryTasks(auth, query),
    { placeholderData: keepPreviousData },
  );
}

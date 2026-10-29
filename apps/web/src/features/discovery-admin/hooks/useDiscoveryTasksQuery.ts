import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import type { TaskListQuery } from "../services/taskListQuery";
import { listDiscoveryTasks } from "../services/discoveryAdminApi";
import type { DiscoveryTaskListResponse } from "../types";

/** One page of the crawler queue for the typed query state. */
export function useDiscoveryTasksQuery(query: TaskListQuery) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<DiscoveryTaskListResponse>(
    queryKeys.discoveryAdmin.tasks(query, locale),
    () => listDiscoveryTasks({ locale, accessToken: accessToken!, query }),
    { enabled: Boolean(accessToken), placeholderData: keepPreviousData },
  );
}

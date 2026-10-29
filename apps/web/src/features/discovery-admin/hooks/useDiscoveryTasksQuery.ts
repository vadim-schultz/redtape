import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { listDiscoveryTasks } from "../services/discoveryAdminApi";
import type { DiscoveryTaskListResponse } from "../types";
import type { DiscoveryTaskFilters } from "./useDiscoveryTaskFilters";

type TaskQuery = Pick<
  DiscoveryTaskFilters,
  "status" | "source" | "kind" | "offset" | "limit"
>;

/** One page of the crawler queue for the current filters. */
export function useDiscoveryTasksQuery({
  status,
  source,
  kind,
  offset,
  limit,
}: TaskQuery) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;
  const query = { status, source, kind, offset, limit };

  return useApiQuery<DiscoveryTaskListResponse>(
    queryKeys.discoveryAdmin.tasks(query, locale),
    () =>
      listDiscoveryTasks({
        locale,
        accessToken: accessToken!,
        status,
        source: source ?? undefined,
        kind: kind ?? undefined,
        offset,
        limit,
      }),
    { enabled: Boolean(accessToken), placeholderData: keepPreviousData },
  );
}

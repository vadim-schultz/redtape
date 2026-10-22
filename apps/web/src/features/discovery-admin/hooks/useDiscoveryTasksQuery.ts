import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { listDiscoveryTasks } from "../services/discoveryAdminApi";
import type { DiscoveryTaskListResponse } from "../types";
import type { DiscoveryTaskFilters } from "./useDiscoveryTaskFilters";

export function useDiscoveryTasksQuery({
  status,
  source,
}: Pick<DiscoveryTaskFilters, "status" | "source">) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<DiscoveryTaskListResponse>(
    queryKeys.discoveryAdmin.tasks(status, source, locale),
    () =>
      listDiscoveryTasks({
        locale,
        accessToken: accessToken!,
        status,
        source: source ?? undefined,
      }),
    { enabled: Boolean(accessToken), placeholderData: keepPreviousData },
  );
}

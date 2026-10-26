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
  kind,
}: Pick<DiscoveryTaskFilters, "status" | "source" | "kind">) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<DiscoveryTaskListResponse>(
    queryKeys.discoveryAdmin.tasks(status, source, kind, locale),
    () =>
      listDiscoveryTasks({
        locale,
        accessToken: accessToken!,
        status,
        source: source ?? undefined,
        kind: kind ?? undefined,
      }),
    { enabled: Boolean(accessToken), placeholderData: keepPreviousData },
  );
}

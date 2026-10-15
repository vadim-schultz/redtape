import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
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

  return useQuery<DiscoveryTaskListResponse>({
    queryKey: ["discovery-admin", "tasks", status, source, locale],
    queryFn: () =>
      listDiscoveryTasks({
        locale,
        accessToken: accessToken!,
        status,
        source: source ?? undefined,
      }),
    enabled: Boolean(accessToken),
    placeholderData: keepPreviousData,
  });
}

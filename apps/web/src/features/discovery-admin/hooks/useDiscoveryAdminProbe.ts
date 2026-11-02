import { queryKeys } from "../../../app/queryKeys";
import { retryDelay, shouldRetry } from "../../../app/retryPolicy";
import { useAuth } from "../../auth/contexts/AuthContext";
import { probeDiscoveryAdminAccess } from "../services/discoveryAdminApi";
import { useAdminQuery } from "./useAdminQuery";

const MAX_PROBE_RETRIES = 2;

export function useDiscoveryAdminProbe() {
  const { status } = useAuth();

  return useAdminQuery(
    (locale) => queryKeys.discoveryAdmin.probe(locale),
    probeDiscoveryAdminAccess,
    {
      enabled: status === "authenticated",
      retry: (failureCount, error) =>
        failureCount < MAX_PROBE_RETRIES && shouldRetry(failureCount, error),
      retryDelay,
    },
  );
}

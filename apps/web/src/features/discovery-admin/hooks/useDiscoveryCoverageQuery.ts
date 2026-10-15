import { useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { useAuth } from "../../auth/contexts/AuthContext";
import { fetchDiscoveryCoverage } from "../services/discoveryAdminApi";
import type { DiscoveryCoverageResponse } from "../types";

/** Load admin coverage metrics for catalogue index chips. */
export function useDiscoveryCoverageQuery() {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useQuery<DiscoveryCoverageResponse>({
    queryKey: ["discovery-admin", "coverage", locale],
    queryFn: () =>
      fetchDiscoveryCoverage({
        locale,
        accessToken: accessToken!,
      }),
    enabled: Boolean(accessToken),
  });
}

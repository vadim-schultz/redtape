import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { fetchDiscoveryCoverage } from "../services/discoveryAdminApi";
import type { DiscoveryCoverageResponse } from "../types";

/** Load admin coverage metrics for catalogue index chips. */
export function useDiscoveryCoverageQuery() {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<DiscoveryCoverageResponse>(
    queryKeys.discoveryAdmin.coverage(locale),
    () => fetchDiscoveryCoverage({ locale, accessToken: accessToken! }),
    { enabled: Boolean(accessToken) },
  );
}

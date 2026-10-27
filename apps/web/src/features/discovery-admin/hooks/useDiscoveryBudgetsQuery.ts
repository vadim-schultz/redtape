import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { fetchDiscoveryBudgets } from "../services/discoveryAdminApi";
import type { DiscoveryBudgetsResponse } from "../types";

/** Load the free-tier budgets shown as read-only meters on the coverage page. */
export function useDiscoveryBudgetsQuery() {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<DiscoveryBudgetsResponse>(
    queryKeys.discoveryAdmin.budgets(locale),
    () => fetchDiscoveryBudgets({ locale, accessToken: accessToken! }),
    { enabled: Boolean(accessToken) },
  );
}

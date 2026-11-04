import { queryKeys } from "../../../app/queryKeys";
import { fetchDiscoveryBudgets } from "../services/discoveryAdminApi";
import type { DiscoveryBudgetsResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** Load the free-tier budgets shown as read-only meters on the coverage page. */
export function useDiscoveryBudgetsQuery() {
  return useAdminQuery<DiscoveryBudgetsResponse>(
    (locale) => queryKeys.discoveryAdmin.budgets(locale),
    fetchDiscoveryBudgets,
  );
}

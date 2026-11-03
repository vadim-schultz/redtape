import { queryKeys } from "../../../app/queryKeys";
import { fetchDiscoveryCoverage } from "../services/discoveryAdminApi";
import type { DiscoveryCoverageResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** Load admin coverage metrics for catalogue index chips. */
export function useDiscoveryCoverageQuery() {
  return useAdminQuery<DiscoveryCoverageResponse>(
    (locale) => queryKeys.discoveryAdmin.coverage(locale),
    fetchDiscoveryCoverage,
  );
}

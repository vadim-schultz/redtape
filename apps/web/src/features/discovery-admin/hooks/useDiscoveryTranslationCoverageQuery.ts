import { queryKeys } from "../../../app/queryKeys";
import { fetchTranslationCoverage } from "../services/discoveryAdminApi";
import type { TranslationCoverageResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** Load the per-locale card translation coverage, on its own query so the other coverage sections survive a failure. */
export function useDiscoveryTranslationCoverageQuery() {
  return useAdminQuery<TranslationCoverageResponse>(
    (locale) => queryKeys.discoveryAdmin.translationCoverage(locale),
    fetchTranslationCoverage,
  );
}

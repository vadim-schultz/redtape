import { queryKeys } from "../../../app/queryKeys";
import { FLOW_REFRESH_MS } from "../constants/queryTiming";
import { fetchDiscoveryFlow } from "../services/discoveryAdminApi";
import type { DiscoveryFlowResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** Load the pipeline flow, refetched every minute while the page is open. */
export function useDiscoveryFlowQuery() {
  return useAdminQuery<DiscoveryFlowResponse>(
    (locale) => queryKeys.discoveryAdmin.flow(locale),
    fetchDiscoveryFlow,
    { refetchInterval: FLOW_REFRESH_MS },
  );
}

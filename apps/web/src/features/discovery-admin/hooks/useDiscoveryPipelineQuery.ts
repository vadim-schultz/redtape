import { queryKeys } from "../../../app/queryKeys";
import { fetchCataloguePipeline } from "../services/discoveryAdminApi";
import type { CataloguePipelineResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** Load the full staging slice for one catalogue service. */
export function useDiscoveryPipelineQuery(catalogueId: string | undefined) {
  return useAdminQuery<CataloguePipelineResponse>(
    (locale) => queryKeys.discoveryAdmin.pipeline(catalogueId, locale),
    catalogueId
      ? (auth) => fetchCataloguePipeline(auth, catalogueId)
      : undefined,
  );
}

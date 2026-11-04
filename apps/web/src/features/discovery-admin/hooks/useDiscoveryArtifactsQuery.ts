import { queryOptions, skipToken } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import {
  listCatalogueArtifacts,
  type AdminAuth,
} from "../services/discoveryAdminApi";
import type { DiscoveryArtifactListResponse } from "../types";
import { ARTIFACT_STALE_MS } from "../constants/queryTiming";
import { useAdminQueryFromOptions } from "./useAdminQuery";

/** Build the artifact query for one catalogue row. */
export function catalogueArtifactsQueryOptions(
  auth: AdminAuth,
  catalogueId: string | undefined,
) {
  return queryOptions({
    queryKey: queryKeys.discoveryAdmin.artifacts(catalogueId, auth.locale),
    queryFn: catalogueId
      ? () => listCatalogueArtifacts(auth, catalogueId)
      : skipToken,
    staleTime: ARTIFACT_STALE_MS,
    refetchOnWindowFocus: true,
  });
}

/** Load the artifacts of one catalogue row, refreshing their presigned URLs once stale. */
export function useDiscoveryArtifactsQuery(catalogueId: string | undefined) {
  return useAdminQueryFromOptions<DiscoveryArtifactListResponse>((auth) =>
    catalogueArtifactsQueryOptions(auth, catalogueId),
  );
}

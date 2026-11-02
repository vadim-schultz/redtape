import { queryKeys } from "../../../app/queryKeys";
import { listCatalogueArtifacts } from "../services/discoveryAdminApi";
import type { DiscoveryArtifactListResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** Four minutes: shorter than the five minute presign lifetime, so a shown URL is never expired. */
export const ARTIFACT_STALE_MS = 4 * 60 * 1000;

/** Load the artifacts of one catalogue row, refreshing their presigned URLs once stale. */
export function useDiscoveryArtifactsQuery(catalogueId: string | undefined) {
  return useAdminQuery<DiscoveryArtifactListResponse>(
    (locale) => queryKeys.discoveryAdmin.artifacts(catalogueId, locale),
    catalogueId
      ? (auth) => listCatalogueArtifacts(auth, catalogueId)
      : undefined,
    { staleTime: ARTIFACT_STALE_MS, refetchOnWindowFocus: true },
  );
}

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { listCatalogueArtifacts } from "../services/discoveryAdminApi";
import type { DiscoveryArtifactListResponse } from "../types";

/** Four minutes: shorter than the five minute presign lifetime, so a shown URL is never expired. */
export const ARTIFACT_STALE_MS = 4 * 60 * 1000;

/** Load the artifacts of one catalogue row, refreshing their presigned URLs once stale. */
export function useDiscoveryArtifactsQuery(catalogueId: string | undefined) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<DiscoveryArtifactListResponse>(
    queryKeys.discoveryAdmin.artifacts(catalogueId, locale),
    () =>
      listCatalogueArtifacts({
        locale,
        accessToken: accessToken!,
        catalogueId: catalogueId!,
      }),
    {
      enabled: Boolean(accessToken && catalogueId),
      staleTime: ARTIFACT_STALE_MS,
      refetchOnWindowFocus: true,
    },
  );
}

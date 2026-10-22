import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { fetchCataloguePipeline } from "../services/discoveryAdminApi";
import type { CataloguePipelineResponse } from "../types";

export function useDiscoveryPipelineQuery(catalogueId: string | undefined) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<CataloguePipelineResponse>(
    queryKeys.discoveryAdmin.pipeline(catalogueId, locale),
    () =>
      fetchCataloguePipeline({
        locale,
        accessToken: accessToken!,
        catalogueId: catalogueId!,
      }),
    { enabled: Boolean(accessToken && catalogueId) },
  );
}

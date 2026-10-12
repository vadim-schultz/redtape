import { useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { useAuth } from "../../auth/contexts/AuthContext";
import { fetchCataloguePipeline } from "../services/discoveryAdminApi";
import type { CataloguePipelineResponse } from "../types";

export function useDiscoveryPipelineQuery(catalogueId: string | undefined) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useQuery<CataloguePipelineResponse>({
    queryKey: ["discovery-admin", "pipeline", catalogueId, locale],
    queryFn: () =>
      fetchCataloguePipeline({
        locale,
        accessToken: accessToken!,
        catalogueId: catalogueId!,
      }),
    enabled: Boolean(accessToken && catalogueId),
  });
}

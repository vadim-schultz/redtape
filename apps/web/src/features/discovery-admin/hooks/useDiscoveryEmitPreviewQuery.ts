import { useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { useAuth } from "../../auth/contexts/AuthContext";
import { fetchEmitPreview } from "../services/discoveryAdminApi";
import type { EmitPreviewResponse } from "../types";

export function useDiscoveryEmitPreviewQuery(catalogueId: string | undefined) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useQuery<EmitPreviewResponse>({
    queryKey: ["discovery-admin", "emit-preview", catalogueId, locale],
    queryFn: () =>
      fetchEmitPreview({
        locale,
        accessToken: accessToken!,
        catalogueId: catalogueId!,
      }),
    enabled: Boolean(accessToken && catalogueId),
  });
}

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { fetchEmitPreview } from "../services/discoveryAdminApi";
import type { EmitPreviewResponse } from "../types";

export function useDiscoveryEmitPreviewQuery(catalogueId: string | undefined) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<EmitPreviewResponse>(
    queryKeys.discoveryAdmin.emitPreview(catalogueId, locale),
    () =>
      fetchEmitPreview({
        locale,
        accessToken: accessToken!,
        catalogueId: catalogueId!,
      }),
    { enabled: Boolean(accessToken && catalogueId) },
  );
}

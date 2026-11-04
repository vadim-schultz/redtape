import { queryOptions, skipToken } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import {
  fetchEmitPreview,
  type AdminAuth,
} from "../services/discoveryAdminApi";
import type { EmitPreviewResponse } from "../types";
import { useAdminQueryFromOptions } from "./useAdminQuery";

/** Build the emit-preview query for one catalogue row. */
export function cataloguePreviewQueryOptions(
  auth: AdminAuth,
  catalogueId: string | undefined,
) {
  return queryOptions({
    queryKey: queryKeys.discoveryAdmin.emitPreview(catalogueId, auth.locale),
    queryFn: catalogueId
      ? () => fetchEmitPreview(auth, catalogueId)
      : skipToken,
  });
}

/** Load the suggestion payloads emitting a catalogue service would create. */
export function useDiscoveryEmitPreviewQuery(catalogueId: string | undefined) {
  return useAdminQueryFromOptions<EmitPreviewResponse>((auth) =>
    cataloguePreviewQueryOptions(auth, catalogueId),
  );
}

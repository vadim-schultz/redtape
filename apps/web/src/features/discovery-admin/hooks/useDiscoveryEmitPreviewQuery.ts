import { queryKeys } from "../../../app/queryKeys";
import { fetchEmitPreview } from "../services/discoveryAdminApi";
import type { EmitPreviewResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** Load the suggestion payloads emitting a catalogue service would create. */
export function useDiscoveryEmitPreviewQuery(catalogueId: string | undefined) {
  return useAdminQuery<EmitPreviewResponse>(
    (locale) => queryKeys.discoveryAdmin.emitPreview(catalogueId, locale),
    catalogueId ? (auth) => fetchEmitPreview(auth, catalogueId) : undefined,
  );
}

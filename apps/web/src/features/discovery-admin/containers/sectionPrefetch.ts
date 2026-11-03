import { queryOptions, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useAuth } from "../../auth/contexts/AuthContext";
import { ARTIFACT_STALE_MS } from "../hooks/useDiscoveryArtifactsQuery";
import {
  fetchCandidateEmitPreview,
  fetchCandidateEdges,
  fetchEmitPreview,
  listCandidateArtifacts,
  listCatalogueArtifacts,
  type AdminAuth,
} from "../services/discoveryAdminApi";

/*
 * Query options of the secondary panels, with the same keys and calls as the
 * hooks their section containers use. The prefetch hooks start the requests
 * when the page mounts, so they run in parallel with the main query.
 */

/** Options for the staged edges of one candidate. */
export function candidateEdgesOptions(auth: AdminAuth, candidateId: string) {
  return queryOptions({
    queryKey: queryKeys.discoveryAdmin.candidateEdges(candidateId, auth.locale),
    queryFn: () => fetchCandidateEdges(auth, candidateId),
  });
}

/** Options for the evidence of one candidate. */
export function candidateArtifactsOptions(
  auth: AdminAuth,
  candidateId: string,
) {
  return queryOptions({
    queryKey: queryKeys.discoveryAdmin.candidateArtifacts(
      candidateId,
      auth.locale,
    ),
    queryFn: () => listCandidateArtifacts(auth, candidateId),
    staleTime: ARTIFACT_STALE_MS,
  });
}

/** Options for the emit preview of one candidate. */
export function candidateEmitPreviewOptions(
  auth: AdminAuth,
  candidateId: string,
) {
  return queryOptions({
    queryKey: queryKeys.discoveryAdmin.candidateEmitPreview(
      candidateId,
      auth.locale,
    ),
    queryFn: () => fetchCandidateEmitPreview(auth, candidateId),
  });
}

/** Options for the evidence of one catalogue row. */
export function catalogueArtifactsOptions(
  auth: AdminAuth,
  catalogueId: string,
) {
  return queryOptions({
    queryKey: queryKeys.discoveryAdmin.artifacts(catalogueId, auth.locale),
    queryFn: () => listCatalogueArtifacts(auth, catalogueId),
    staleTime: ARTIFACT_STALE_MS,
  });
}

/** Options for the emit preview of one catalogue row. */
export function cataloguePreviewOptions(auth: AdminAuth, catalogueId: string) {
  return queryOptions({
    queryKey: queryKeys.discoveryAdmin.emitPreview(catalogueId, auth.locale),
    queryFn: () => fetchEmitPreview(auth, catalogueId),
  });
}

/** Start the edges, evidence and emit preview requests of a document while its main record loads. */
export function usePrefetchDocumentSections(candidateId: string | undefined) {
  const queryClient = useQueryClient();
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  useEffect(() => {
    if (!candidateId || !accessToken) return;
    const auth = { locale, accessToken };
    void queryClient.prefetchQuery(candidateEdgesOptions(auth, candidateId));
    void queryClient.prefetchQuery(
      candidateArtifactsOptions(auth, candidateId),
    );
    void queryClient.prefetchQuery(
      candidateEmitPreviewOptions(auth, candidateId),
    );
  }, [queryClient, candidateId, locale, accessToken]);
}

/** Start the evidence and emit preview requests of a catalogue row while its pipeline loads. */
export function usePrefetchPipelineSections(catalogueId: string | undefined) {
  const queryClient = useQueryClient();
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  useEffect(() => {
    if (!catalogueId || !accessToken) return;
    const auth = { locale, accessToken };
    void queryClient.prefetchQuery(
      catalogueArtifactsOptions(auth, catalogueId),
    );
    void queryClient.prefetchQuery(cataloguePreviewOptions(auth, catalogueId));
  }, [queryClient, catalogueId, locale, accessToken]);
}

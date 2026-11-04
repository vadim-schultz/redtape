import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { useLocale } from "../../../contexts/LocaleContext";
import { useAuth } from "../../auth/contexts/AuthContext";
import { candidateEdgesQueryOptions } from "../hooks/useCandidateEdgesQuery";
import { candidateArtifactsQueryOptions } from "../hooks/useDiscoveryCandidateArtifactsQuery";
import { candidateEmitPreviewQueryOptions } from "../hooks/useDiscoveryCandidateEmitPreviewQuery";
import { catalogueArtifactsQueryOptions } from "../hooks/useDiscoveryArtifactsQuery";
import { cataloguePreviewQueryOptions } from "../hooks/useDiscoveryEmitPreviewQuery";

/*
 * The prefetch hooks start the same secondary requests as their section hooks
 * when the page mounts, so they run in parallel with the main query.
 */

/** Start the edges, evidence and emit preview requests of a document while its main record loads. */
export function usePrefetchDocumentSections(candidateId: string | undefined) {
  const queryClient = useQueryClient();
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  useEffect(() => {
    if (!candidateId || !accessToken) return;
    const auth = { locale, accessToken };
    void queryClient.prefetchQuery(
      candidateEdgesQueryOptions(auth, candidateId),
    );
    void queryClient.prefetchQuery(
      candidateArtifactsQueryOptions(auth, candidateId),
    );
    void queryClient.prefetchQuery(
      candidateEmitPreviewQueryOptions(auth, candidateId),
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
      catalogueArtifactsQueryOptions(auth, catalogueId),
    );
    void queryClient.prefetchQuery(
      cataloguePreviewQueryOptions(auth, catalogueId),
    );
  }, [queryClient, catalogueId, locale, accessToken]);
}

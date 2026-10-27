import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import {
  listDiscoveryCandidates,
  type DiscoveryCandidateQuery,
} from "../services/discoveryAdminApi";
import type { DiscoveryCandidateListResponse } from "../types";
import type { DiscoveryDocumentFilters } from "./useDiscoveryDocumentFilters";

function toQuery(filters: DiscoveryDocumentFilters): DiscoveryCandidateQuery {
  return {
    q: filters.q || undefined,
    minMentions: filters.minMentions ?? undefined,
    role: filters.role ?? undefined,
    source: filters.source ?? undefined,
    sort: filters.sort,
    offset: filters.offset,
    limit: filters.limit,
  };
}

/** One page of document candidates for the current filters. */
export function useDiscoveryCandidatesQuery(filters: DiscoveryDocumentFilters) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;
  const query = toQuery(filters);

  return useApiQuery<DiscoveryCandidateListResponse>(
    queryKeys.discoveryAdmin.candidates(query, locale),
    () => listDiscoveryCandidates({ locale, accessToken: accessToken!, query }),
    { enabled: Boolean(accessToken), placeholderData: keepPreviousData },
  );
}

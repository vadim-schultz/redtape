import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import type { SortChange } from "../../../services/listQuery";
import type {
  CandidateListQuery,
  CandidateSortKey,
} from "../services/candidateListQuery";
import { listDiscoveryCandidates } from "../services/discoveryAdminApi";
import type {
  DiscoveryCandidateListResponse,
  DiscoveryCandidateSort,
} from "../types";
import type { DiscoveryDocumentFilters } from "./useDiscoveryDocumentFilters";

/** The select's combined sort values as a key and direction; the table (chapter 4) emits these directly. */
const SELECT_SORTS: Record<
  DiscoveryCandidateSort,
  Required<SortChange<CandidateSortKey>>
> = {
  mentions_desc: { sortBy: "mentions", sortOrder: "desc" },
  title_asc: { sortBy: "title", sortOrder: "asc" },
  newest: { sortBy: "created_at", sortOrder: "desc" },
};

function toQuery(filters: DiscoveryDocumentFilters): CandidateListQuery {
  return {
    offset: filters.offset,
    limit: filters.limit,
    ...SELECT_SORTS[filters.sort],
    search: filters.q || undefined,
    filters: {
      min_mentions: filters.minMentions ?? undefined,
      role: filters.role ?? undefined,
      source: filters.source ?? undefined,
    },
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

import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import type { CandidateListQuery } from "../services/candidateListQuery";
import { listDiscoveryCandidates } from "../services/discoveryAdminApi";
import type { DiscoveryCandidateListResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** One page of document candidates for the typed query state. */
export function useDiscoveryCandidatesQuery(query: CandidateListQuery) {
  return useAdminQuery<DiscoveryCandidateListResponse>(
    (locale) => queryKeys.discoveryAdmin.candidates(query, locale),
    (auth) => listDiscoveryCandidates(auth, query),
    { placeholderData: keepPreviousData },
  );
}

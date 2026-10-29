import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import type { CandidateListQuery } from "../services/candidateListQuery";
import { listDiscoveryCandidates } from "../services/discoveryAdminApi";
import type { DiscoveryCandidateListResponse } from "../types";

/** One page of document candidates for the typed query state. */
export function useDiscoveryCandidatesQuery(query: CandidateListQuery) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<DiscoveryCandidateListResponse>(
    queryKeys.discoveryAdmin.candidates(query, locale),
    () => listDiscoveryCandidates({ locale, accessToken: accessToken!, query }),
    { enabled: Boolean(accessToken), placeholderData: keepPreviousData },
  );
}

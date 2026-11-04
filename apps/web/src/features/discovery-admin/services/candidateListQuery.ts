import {
  defineListSpec,
  minIntFilter,
  oneOfFilter,
  type ListQuerySpec,
  type ListQueryState,
} from "../../../services/listQuery";
import {
  CANDIDATE_SORT_KEYS,
  CANDIDATE_STATUSES,
  COMPLETE_CHOICES,
  DISCOVERY_SOURCES,
  MENTION_ROLES,
  type CandidateFilterKey,
  type CandidateSortKey,
} from "../types";

export type { CandidateFilterKey, CandidateSortKey };
export type CandidateListQuery = ListQueryState<
  CandidateSortKey,
  CandidateFilterKey
>;

/** Mirrors the API allowlist; values the API would refuse never reach a request or the URL state. */
export const CANDIDATE_LIST_SPEC: ListQuerySpec<
  CandidateSortKey,
  CandidateFilterKey
> = defineListSpec({
  sortKeys: CANDIDATE_SORT_KEYS,
  filters: {
    status: oneOfFilter(CANDIDATE_STATUSES),
    role: oneOfFilter(MENTION_ROLES),
    source: oneOfFilter(DISCOVERY_SOURCES),
    min_mentions: minIntFilter(0),
    complete: oneOfFilter(COMPLETE_CHOICES),
  },
});

import {
  minIntFilter,
  oneOfFilter,
  type ListQuerySpec,
  type ListQueryState,
} from "../../../services/listQuery";
import {
  CANDIDATE_STATUSES,
  DISCOVERY_SOURCES,
  MENTION_ROLES,
} from "../types/listValues";
import type { CandidateFilterKey, CandidateSortKey } from "../types";

export type { CandidateFilterKey, CandidateSortKey };
export type CandidateListQuery = ListQueryState<
  CandidateSortKey,
  CandidateFilterKey
>;

const SORT_KEYS = [
  "mentions",
  "title",
  "created_at",
  "jurisdiction",
  "status",
  "roles",
  "completeness",
] as const satisfies readonly CandidateSortKey[];
const COMPLETE_CHOICES = ["yes", "no"] as const;
/** Mirrors the API allowlist; values the API would refuse never reach a request or the URL state. */
export const CANDIDATE_LIST_SPEC: ListQuerySpec<
  CandidateSortKey,
  CandidateFilterKey
> = {
  sortKeys: SORT_KEYS,
  filters: {
    status: oneOfFilter(CANDIDATE_STATUSES),
    role: oneOfFilter(MENTION_ROLES),
    source: oneOfFilter(DISCOVERY_SOURCES),
    min_mentions: minIntFilter(0),
    complete: oneOfFilter(COMPLETE_CHOICES),
  },
  defaultLimit: 20,
  maxLimit: 100,
};

import {
  minIntFilter,
  oneOfFilter,
  type ListQuerySpec,
  type ListQueryState,
} from "../../../services/listQuery";
import { DISCOVERY_SOURCES } from "../types/listValues";
import type {
  CandidateFilterKey,
  CandidateSortKey,
  DiscoveryCandidateStatus,
  DiscoveryMentionRole,
} from "../types";

export type { CandidateFilterKey, CandidateSortKey };
export type CandidateListQuery = ListQueryState<
  CandidateSortKey,
  CandidateFilterKey
>;

const SORT_KEYS = [
  "mentions",
  "title",
  "created_at",
] as const satisfies readonly CandidateSortKey[];
const STATUSES = [
  "staged",
  "emitted",
] as const satisfies readonly DiscoveryCandidateStatus[];
const ROLES = [
  "required",
  "form",
  "issued",
] as const satisfies readonly DiscoveryMentionRole[];
/** Mirrors the API allowlist; values the API would refuse never reach a request or the URL state. */
export const CANDIDATE_LIST_SPEC: ListQuerySpec<
  CandidateSortKey,
  CandidateFilterKey
> = {
  sortKeys: SORT_KEYS,
  filters: {
    status: oneOfFilter(STATUSES),
    role: oneOfFilter(ROLES),
    source: oneOfFilter(DISCOVERY_SOURCES),
    min_mentions: minIntFilter(0),
  },
  defaultLimit: 20,
  maxLimit: 100,
};

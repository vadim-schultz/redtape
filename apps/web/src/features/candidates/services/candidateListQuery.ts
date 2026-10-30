import {
  oneOfFilter,
  type FilterValue,
  type ListQuerySpec,
  type ListQueryState,
} from "../../../services/listQuery";
import type { CandidateFilterKey, CandidateSortKey } from "../types";

export type CandidateListQuery = ListQueryState<
  CandidateSortKey,
  CandidateFilterKey
>;

const SORT_KEYS = [
  "completeness",
  "title",
  "mentions",
  "created_at",
] as const satisfies readonly CandidateSortKey[];

/** A taxonomy code: any non-blank text; the API answers 422 for an unknown one. */
function codeFilter(raw: string): FilterValue | undefined {
  return raw.trim() || undefined;
}

/** Mirrors the public API allowlist; values it would refuse never reach a request or the URL state. */
export const CANDIDATE_LIST_SPEC: ListQuerySpec<
  CandidateSortKey,
  CandidateFilterKey
> = {
  sortKeys: SORT_KEYS,
  filters: {
    complete: oneOfFilter(["yes", "no"] as const),
    domain: codeFilter,
    situation: codeFilter,
  },
  defaultLimit: 20,
  maxLimit: 100,
};

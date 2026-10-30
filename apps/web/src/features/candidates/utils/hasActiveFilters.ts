import type { CandidateList } from "../hooks/useCandidateListState";

/** True while any taxonomy or completeness filter narrows the list; search does not count. */
export function hasActiveFilters(state: CandidateList["state"]): boolean {
  return Object.keys(state.filters).length > 0;
}

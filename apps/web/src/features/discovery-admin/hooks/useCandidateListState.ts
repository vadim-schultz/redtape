import {
  useListQueryState,
  type ListQueryController,
} from "../../../hooks/useListQueryState";
import { CANDIDATE_LIST_SPEC } from "../services/candidateListQuery";
import type { CandidateFilterKey, CandidateSortKey } from "../types";

/** The URL-backed query controls of the documents list. */
export type CandidateList = ListQueryController<
  CandidateSortKey,
  CandidateFilterKey
>;

/** Search, filter, sort and page of the documents list, read from and written to the URL. */
export function useCandidateListState(): CandidateList {
  return useListQueryState(CANDIDATE_LIST_SPEC);
}

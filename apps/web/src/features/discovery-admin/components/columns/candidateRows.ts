import type { DiscoveryCandidate } from "../../types";

/** The order the API applies when no sort is requested; the header shows it as the active sort. */
export const DEFAULT_CANDIDATE_SORT = {
  sortBy: "mentions",
  sortOrder: "desc",
} as const;

/** Where a candidate's detail page lives. */
export const candidateHref = (candidate: DiscoveryCandidate) =>
  `/admin/discovery/documents/${candidate.id}`;

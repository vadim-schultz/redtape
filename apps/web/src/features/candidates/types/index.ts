import type { CategoryTag } from "../../taxonomy/types";

export type { CategoryTag };

/** How a list was produced: no query, both retrieval legs, or full text alone (flag off or no vector). */
export const SEARCH_MODES = ["browse", "hybrid", "keyword"] as const;

export type SearchMode = (typeof SEARCH_MODES)[number];

/** One candidate of the ranked public list; `confidence` is the filter-aware card confidence. */
export type CandidateCard = {
  id: string;
  key: string;
  title: string;
  description: string | null;
  description_source: string | null;
  categories: CategoryTag[];
  mention_count: number;
  confidence: number;
  /** The combined ranking score; older APIs omit it. */
  score?: number;
  /** Query match in 0..1, only on hybrid matches; null or absent otherwise. */
  similarity?: number | null;
};

export type CandidateListResponse = {
  items: CandidateCard[];
  total: number;
  offset: number;
  limit: number;
  /** Absent on older APIs, which only browse. */
  search_mode?: SearchMode;
};

export * from "./detail";

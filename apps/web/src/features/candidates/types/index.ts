import type { CategoryTag } from "../../taxonomy/types";

export type { CategoryTag };

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
};

export type CandidateListResponse = {
  items: CandidateCard[];
  total: number;
  offset: number;
  limit: number;
};

export * from "./detail";

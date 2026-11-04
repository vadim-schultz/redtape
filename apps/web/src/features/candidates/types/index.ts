import type { CategoryTag } from "../../taxonomy/types";
import type { CompletenessFlags } from "../../../components/data-display/CompletenessChips/types";

export type { CategoryTag };
export type { CompletenessFlags };
export type CandidateStatus = "staged" | "emitted";

/** One candidate of the ranked public list; `confidence` is the filter-aware card confidence. */
export type CandidateCard = {
  id: string;
  key: string;
  title: string;
  description: string | null;
  description_source: string | null;
  status: CandidateStatus;
  categories: CategoryTag[];
  completeness: number;
  complete: boolean;
  flags: CompletenessFlags;
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

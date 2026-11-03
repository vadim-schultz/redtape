/** A scored taxonomy code with its localized name; `confidence` is its score in `[0, 1]`. */
export type TaxonomyTag = {
  code: string;
  name: string;
  confidence: number;
};

import type { CompletenessFlags } from "../../../components/data-display/CompletenessChips/types";

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
  domains: TaxonomyTag[];
  situations: TaxonomyTag[];
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

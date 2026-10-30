/** An accepted taxonomy code with its localized name. */
export type TaxonomyTag = {
  code: string;
  name: string;
};

/** The five completeness flags of a candidate, as the public API nests them. */
export type CompletenessFlags = {
  has_domain: boolean;
  has_situation: boolean;
  has_edges: boolean;
  has_snapshot: boolean;
  has_screenshot: boolean;
};

export type CandidateStatus = "staged" | "emitted";

/** One candidate of the ranked public list. */
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
};

export type CandidateListResponse = {
  items: CandidateCard[];
  total: number;
  offset: number;
  limit: number;
};

export type CandidateSortKey =
  "completeness" | "title" | "mentions" | "created_at";

export type CandidateFilterKey = "complete" | "domain" | "situation";

export * from "./detail";

/** A staged "parent requires required" edge with both titles and the stating procedure. */
export type DiscoveryCandidateEdge = {
  id: string;
  parent_candidate_id: string;
  parent_title_i18n: Record<string, string>;
  required_candidate_id: string;
  required_title_i18n: Record<string, string>;
  catalogue_service_id: string;
  procedure_title_i18n: Record<string, string>;
  /** Open set: `explicit`, `derived_single_issued`. */
  basis: string;
  condition: string | null;
  is_optional: boolean | null;
  excerpt: string;
  extractor: string;
  extractor_version: string;
  created_at: string;
};

/** Every edge that has the candidate as parent or as required end. */
export type DiscoveryCandidateEdgesResponse = {
  items: DiscoveryCandidateEdge[];
};

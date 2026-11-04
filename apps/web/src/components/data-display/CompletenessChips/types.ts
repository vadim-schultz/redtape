/** The five completeness flags of a candidate, as the public API nests them. */
export type CompletenessFlags = {
  has_domain: boolean;
  has_situation: boolean;
  has_edges: boolean;
  has_snapshot: boolean;
  has_screenshot: boolean;
};

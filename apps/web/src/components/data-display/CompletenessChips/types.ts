/** The four completeness flags of a candidate, as the public API nests them. */
export type CompletenessFlags = {
  has_category: boolean;
  has_edges: boolean;
  has_snapshot: boolean;
  has_screenshot: boolean;
};

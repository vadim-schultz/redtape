// Closed sets of the suggestions list. Each array is declared once; the types derive.

/** Suggestion kinds the API returns. */
export const SUGGESTION_KINDS = ["new_document", "new_requirement"] as const;
export type SuggestionKind = (typeof SUGGESTION_KINDS)[number];

/** Suggestion statuses the API returns. */
export const SUGGESTION_STATUSES = ["pending", "approved", "rejected"] as const;
export type SuggestionStatus = (typeof SUGGESTION_STATUSES)[number];

/** Status choices of the list filter: the statuses plus `all`, in display order. */
export const SUGGESTION_STATUS_FILTERS = [
  "pending",
  "all",
  "approved",
  "rejected",
] as const;
export type SuggestionStatusFilter = (typeof SUGGESTION_STATUS_FILTERS)[number];

/** Who submitted a suggestion. */
export const SUGGESTION_SOURCES = ["human", "crawler"] as const;
export type SuggestionSourceType = (typeof SUGGESTION_SOURCES)[number];

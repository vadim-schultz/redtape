import type {
  CandidateCard,
  CompletenessFlags,
} from "../features/candidates/types";

export const ALL_FLAGS: CompletenessFlags = {
  has_domain: true,
  has_situation: true,
  has_edges: true,
  has_snapshot: true,
  has_screenshot: true,
};

/** A complete candidate card as the public API returns it; override what a test needs. */
export function candidateFixture(
  overrides: Partial<CandidateCard> = {},
): CandidateCard {
  return {
    id: "c1",
    key: "passport",
    title: "Passport",
    description: "Proof of identity.",
    description_source: "Apply for a passport",
    domains: [{ code: "identity", name: "Identity" }],
    situations: [{ code: "moving", name: "Moving" }],
    status: "staged",
    completeness: 5,
    complete: true,
    flags: ALL_FLAGS,
    mention_count: 3,
    ...overrides,
  };
}

/** The list envelope of the public candidate API. */
export function candidatePage(
  items: CandidateCard[],
  total = items.length,
  offset = 0,
) {
  return { items, total, offset, limit: 20 };
}

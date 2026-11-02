import type {
  CandidateCard,
  CandidateDetail,
  CandidateNeighbour,
  CandidateSource,
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
    domains: [{ code: "identity", name: "Identity", confidence: 0.8 }],
    situations: [{ code: "moving", name: "Moving", confidence: 0.6 }],
    status: "staged",
    completeness: 5,
    complete: true,
    flags: ALL_FLAGS,
    mention_count: 3,
    confidence: 0.8,
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

/** One ingress or egress neighbour as the detail endpoint returns it. */
export function neighbourFixture(
  overrides: Partial<CandidateNeighbour> = {},
): CandidateNeighbour {
  return {
    id: "n1",
    title: "Birth certificate",
    description: "Issued by the registry office.",
    condition: null,
    is_optional: false,
    excerpt: "Please bring your birth certificate.",
    basis: "explicit",
    procedure_title: "Apply for a passport",
    ...overrides,
  };
}

/** One source page of a candidate. */
export function sourceFixture(
  overrides: Partial<CandidateSource> = {},
): CandidateSource {
  return {
    procedure_title: "Apply for a passport",
    portal_url: "https://portal.example/passport",
    role: "required",
    excerpt: "A valid passport is required.",
    condition: null,
    is_optional: false,
    ...overrides,
  };
}

/** A fully described candidate detail; override what a test needs. */
export function candidateDetailFixture(
  overrides: Partial<CandidateDetail> = {},
): CandidateDetail {
  return {
    ...candidateFixture(),
    ingress: [],
    ingress_truncated: false,
    egress: [],
    egress_truncated: false,
    sources: [sourceFixture()],
    screenshot: { url: "/shot", fetched_at: "2026-10-01T10:00:00Z" },
    ...overrides,
  };
}

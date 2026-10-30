import type { CandidateCard } from "./index";

export type EdgeBasis = "explicit" | "derived_single_issued";

export type SourceRole = "required" | "form" | "issued";

/** A document on the other end of one requirement edge, as the API reads the edge. */
export type CandidateNeighbour = {
  id: string;
  title: string;
  description: string | null;
  condition: string | null;
  is_optional: boolean;
  excerpt: string;
  basis: EdgeBasis;
  procedure_title: string;
};

/** A procedure page that mentions the candidate, with the quote that names it. */
export type CandidateSource = {
  procedure_title: string;
  portal_url: string | null;
  role: SourceRole;
  excerpt: string;
  condition: string | null;
  is_optional: boolean;
};

export type CandidateScreenshot = {
  url: string;
  fetched_at: string;
};

/** One candidate with its dependency neighbours and evidence. */
export type CandidateDetail = CandidateCard & {
  ingress: CandidateNeighbour[];
  ingress_truncated: boolean;
  egress: CandidateNeighbour[];
  egress_truncated: boolean;
  sources: CandidateSource[];
  screenshot: CandidateScreenshot | null;
};

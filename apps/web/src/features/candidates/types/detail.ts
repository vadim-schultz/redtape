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

/** One capture of a candidate's screenshot history: its relative proxy path and when it was fetched. */
export type CandidateScreenshot = {
  url: string;
  fetched_at: string;
};

/** One capture ready to show: the absolute image URL and when it was fetched. */
export type ScreenshotCapture = {
  src: string;
  fetchedAt: string;
};

/**
 * One candidate with its dependency neighbours and evidence.
 *
 * `screenshots` is the history, newest first; it is absent on an API that predates it,
 * where `screenshot` (the newest, on the legacy route) is the only capture.
 */
export type CandidateDetail = CandidateCard & {
  ingress: CandidateNeighbour[];
  ingress_truncated: boolean;
  egress: CandidateNeighbour[];
  egress_truncated: boolean;
  sources: CandidateSource[];
  screenshot: CandidateScreenshot | null;
  screenshots?: CandidateScreenshot[];
};

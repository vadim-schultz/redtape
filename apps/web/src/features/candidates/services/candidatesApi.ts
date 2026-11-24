import { buildApiUrl } from "../../../services/apiOrigin";
import { apiRequest } from "../../../services/api";
import type {
  CandidateDetail,
  CandidateScreenshot,
  ScreenshotCapture,
} from "../types";

/** One candidate with its neighbours and evidence; a 404 means no such candidate. */
export async function fetchCandidate(params: {
  locale: string;
  id: string;
}): Promise<CandidateDetail> {
  const { locale, id } = params;
  return apiRequest<CandidateDetail>(
    `/api/v1/candidates/${encodeURIComponent(id)}`,
    { locale },
  );
}

/** Where the browser loads a candidate's newest screenshot from: the legacy public proxy route. */
export function candidateScreenshotUrl(id: string): string {
  return buildApiUrl(
    `/api/v1/candidates/${encodeURIComponent(id)}/screenshot`,
  ).toString();
}

function captureOf(shot: CandidateScreenshot): ScreenshotCapture {
  return { src: buildApiUrl(shot.url).toString(), fetchedAt: shot.fetched_at };
}

function newestCapture(candidate: CandidateDetail): ScreenshotCapture[] {
  if (!candidate.screenshot) return [];
  return [
    {
      src: candidateScreenshotUrl(candidate.id),
      fetchedAt: candidate.screenshot.fetched_at,
    },
  ];
}

/** The captures to show, newest first: the history when the API sends it, else its newest screenshot. */
export function candidateCaptures(
  candidate: CandidateDetail,
): ScreenshotCapture[] {
  const history = candidate.screenshots ?? [];
  if (history.length > 0) return history.map(captureOf);
  return newestCapture(candidate);
}

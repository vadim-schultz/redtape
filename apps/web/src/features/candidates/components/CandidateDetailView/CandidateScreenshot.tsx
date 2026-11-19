import type { ScreenshotCapture } from "../../types";
import CandidateCapture from "./CandidateCapture";
import CandidateScreenshotTabs from "./CandidateScreenshotTabs";

export interface CandidateScreenshotProps {
  /** The captures, newest first; an empty list means the detail has no screenshot. */
  captures: ScreenshotCapture[];
  title: string;
}

/** The screenshot evidence: one capture as a single image, two or more as the history in tabs. */
export default function CandidateScreenshot({
  captures,
  title,
}: CandidateScreenshotProps) {
  if (captures.length > 1)
    return <CandidateScreenshotTabs captures={captures} title={title} />;
  return <CandidateCapture capture={captures[0]} title={title} />;
}

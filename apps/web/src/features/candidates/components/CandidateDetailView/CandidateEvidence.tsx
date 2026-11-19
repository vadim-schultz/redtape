import { VStack } from "@chakra-ui/react";

import type { CandidateDetail, ScreenshotCapture } from "../../types";
import CandidateScreenshot from "./CandidateScreenshot";

export interface CandidateEvidenceProps {
  candidate: Pick<CandidateDetail, "title">;
  captures: ScreenshotCapture[];
}

/** Render the screenshot evidence body; the parent accordion owns its heading. */
export default function CandidateEvidence({
  candidate,
  captures,
}: CandidateEvidenceProps) {
  return (
    <VStack align="stretch" gap={4}>
      <CandidateScreenshot captures={captures} title={candidate.title} />
    </VStack>
  );
}

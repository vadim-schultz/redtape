import { VStack } from "@chakra-ui/react";

import type { CandidateDetail } from "../../types";
import CandidateScreenshot from "./CandidateScreenshot";

export interface CandidateEvidenceProps {
  candidate: Pick<CandidateDetail, "title" | "screenshot">;
  screenshotUrl: string;
}

/** Render the screenshot evidence body; the parent accordion owns its heading. */
export default function CandidateEvidence({
  candidate,
  screenshotUrl,
}: CandidateEvidenceProps) {
  const { title, screenshot } = candidate;

  return (
    <VStack align="stretch" gap={4}>
      <CandidateScreenshot
        src={screenshot ? screenshotUrl : null}
        title={title}
        fetchedAt={screenshot?.fetched_at ?? null}
      />
    </VStack>
  );
}

import { VStack } from "@chakra-ui/react";

import type { CandidateDetail } from "../../types";
import CandidateChecklist from "./CandidateChecklist";
import CandidateEvidence from "./CandidateEvidence";
import CandidateHeader from "./CandidateHeader";
import NeighbourSection from "./NeighbourSection";

export interface CandidateDetailContentProps {
  candidate: CandidateDetail;
  screenshotUrl: string;
}

/** A loaded candidate, top to bottom; the flow diagram section joins between the lists and the evidence. */
export default function CandidateDetailContent({
  candidate,
  screenshotUrl,
}: CandidateDetailContentProps) {
  return (
    <VStack align="stretch" gap={8}>
      <CandidateHeader candidate={candidate} />
      <CandidateChecklist
        flags={candidate.flags}
        completeness={candidate.completeness}
      />
      <NeighbourSection kind="ingress" items={candidate.ingress} />
      <NeighbourSection kind="egress" items={candidate.egress} />
      <CandidateEvidence candidate={candidate} screenshotUrl={screenshotUrl} />
    </VStack>
  );
}

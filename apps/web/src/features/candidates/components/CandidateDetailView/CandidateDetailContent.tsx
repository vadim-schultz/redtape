import { VStack } from "@chakra-ui/react";

import type { CandidateDetail } from "../../types";
import CandidateEvidence from "./CandidateEvidence";
import CandidateHeader from "./CandidateHeader";
import { FlowSection } from "../FlowDiagram";
import NeighbourSection from "./NeighbourSection";

export interface CandidateDetailContentProps {
  candidate: CandidateDetail;
  screenshotUrl: string;
}

/** A loaded candidate, top to bottom; the flow section sits between the lists and the evidence. */
export default function CandidateDetailContent({
  candidate,
  screenshotUrl,
}: CandidateDetailContentProps) {
  return (
    <VStack align="stretch" gap={8}>
      <CandidateHeader candidate={candidate} />
      <NeighbourSection kind="ingress" items={candidate.ingress} />
      <NeighbourSection kind="egress" items={candidate.egress} />
      <FlowSection candidate={candidate} />
      <CandidateEvidence candidate={candidate} screenshotUrl={screenshotUrl} />
    </VStack>
  );
}

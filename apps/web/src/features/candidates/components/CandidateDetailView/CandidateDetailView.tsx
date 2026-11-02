import { VStack } from "@chakra-ui/react";

import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import type { CandidateDetail } from "../../types";
import { CandidatesBanner } from "../CandidatesBanner";
import CandidateBackButton from "./CandidateBackButton";
import CandidateDetailQueryStatus from "./CandidateDetailQueryStatus";

export interface CandidateDetailViewProps {
  status: QueryStatus;
  candidate: CandidateDetail | undefined;
  screenshotUrl: string;
}

/** The public item page: back link to the documents list and the unreviewed notice in every state, then the candidate. */
export default function CandidateDetailView(props: CandidateDetailViewProps) {
  return (
    <VStack align="stretch" gap={6}>
      <CandidateBackButton />
      <CandidatesBanner />
      <CandidateDetailQueryStatus {...props} />
    </VStack>
  );
}

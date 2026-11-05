import { VStack } from "@chakra-ui/react";

import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import type { CandidateDetail } from "../../types";
import CandidateBackButton from "./CandidateBackButton";
import CandidateDetailQueryStatus from "./CandidateDetailQueryStatus";

export interface CandidateDetailViewProps {
  status: QueryStatus;
  candidate: CandidateDetail | undefined;
  screenshotUrl: string;
}

/** The public item page: back link to the documents list and the candidate content in every query state. */
export default function CandidateDetailView(props: CandidateDetailViewProps) {
  return (
    <VStack align="stretch" gap={6}>
      <CandidateBackButton />
      <CandidateDetailQueryStatus {...props} />
    </VStack>
  );
}

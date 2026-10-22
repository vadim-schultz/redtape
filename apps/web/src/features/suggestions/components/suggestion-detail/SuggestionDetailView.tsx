import { Box, VStack } from "@chakra-ui/react";

import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import type { SuggestionRead } from "../../types";

import SuggestionBackButton from "./SuggestionBackButton";
import SuggestionDetailQueryStatus from "./SuggestionDetailQueryStatus";

export interface SuggestionDetailViewProps {
  suggestion: SuggestionRead | undefined;
  status: QueryStatus;
  onBack: () => void;
}

export default function SuggestionDetailView({
  suggestion,
  status,
  onBack,
}: SuggestionDetailViewProps) {
  return (
    <Box>
      <VStack align="stretch" gap={4}>
        <SuggestionBackButton onBack={onBack} />
        <SuggestionDetailQueryStatus suggestion={suggestion} status={status} />
      </VStack>
    </Box>
  );
}

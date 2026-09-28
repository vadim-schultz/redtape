import { Box, VStack } from "@chakra-ui/react";

import type { SuggestionRead } from "../../types";

import SuggestionBackButton from "./SuggestionBackButton";
import SuggestionDetailQueryStatus from "./SuggestionDetailQueryStatus";

export interface SuggestionDetailViewProps {
  suggestion: SuggestionRead | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  onBack: () => void;
}

export default function SuggestionDetailView({
  onBack,
  ...status
}: SuggestionDetailViewProps) {
  return (
    <Box>
      <VStack align="stretch" gap={4}>
        <SuggestionBackButton onBack={onBack} />
        <SuggestionDetailQueryStatus {...status} />
      </VStack>
    </Box>
  );
}

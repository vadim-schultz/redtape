import { Box, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import type { SuggestionRead } from "../../types";

import SuggestionsListHeader from "./SuggestionsListHeader";
import SuggestionsListQueryStatus from "./SuggestionsListQueryStatus";

export interface SuggestionsListViewProps {
  title: string;
  filters: ReactNode;
  suggestions: SuggestionRead[] | undefined;
  isLoading: boolean;
  isRefreshing: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
}

export default function SuggestionsListView({
  title,
  filters,
  ...status
}: SuggestionsListViewProps) {
  return (
    <Box>
      <SuggestionsListHeader title={title} />

      <Box mt={6}>{filters}</Box>

      <Box mt={6}>
        <VStack align="stretch" gap={3}>
          <SuggestionsListQueryStatus {...status} />
        </VStack>
      </Box>
    </Box>
  );
}

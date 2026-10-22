import { Box, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import type { SuggestionRead } from "../../types";

import SuggestionsListHeader from "./SuggestionsListHeader";
import SuggestionsListQueryStatus from "./SuggestionsListQueryStatus";

export interface SuggestionsListViewProps {
  title: string;
  filters: ReactNode;
  list: {
    suggestions: SuggestionRead[] | undefined;
    status: QueryStatus;
  };
}

export default function SuggestionsListView({
  title,
  filters,
  list,
}: SuggestionsListViewProps) {
  return (
    <Box>
      <SuggestionsListHeader title={title} />

      <Box mt={6}>{filters}</Box>

      <Box mt={6}>
        <VStack align="stretch" gap={3}>
          <SuggestionsListQueryStatus {...list} />
        </VStack>
      </Box>
    </Box>
  );
}

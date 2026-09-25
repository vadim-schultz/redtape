import { Box, VStack } from "@chakra-ui/react";

import type { DocumentDetail } from "../../types";

import DocumentBackButton from "./DocumentBackButton";
import DocumentDetailQueryStatus from "./DocumentDetailQueryStatus";

export interface DocumentDetailViewProps {
  document: DocumentDetail | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  onBack: () => void;
  requirementsTitle: string;
  noRequirementsLabel: string;
  officialSourceTitle: string;
}

export default function DocumentDetailView({
  onBack,
  ...status
}: DocumentDetailViewProps) {
  return (
    <Box>
      <VStack align="stretch" gap={4}>
        <DocumentBackButton onBack={onBack} />
        <DocumentDetailQueryStatus {...status} />
      </VStack>
    </Box>
  );
}

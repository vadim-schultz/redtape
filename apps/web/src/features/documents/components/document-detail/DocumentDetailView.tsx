import { Box, VStack } from "@chakra-ui/react";

import type { DocumentDetail } from "../../types";

import DocumentBackButton from "./DocumentBackButton";
import DocumentDetailQueryStatus from "./DocumentDetailQueryStatus";

export interface DocumentDetailViewProps {
  document: DocumentDetail | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  onBack: () => void;
  requirementsTitle: string;
  noRequirementsLabel: string;
  officialSourceTitle: string;
}

export default function DocumentDetailView({
  document,
  isLoading,
  isError,
  onBack,
  requirementsTitle,
  noRequirementsLabel,
  officialSourceTitle,
}: DocumentDetailViewProps) {
  return (
    <Box>
      <VStack align="stretch" gap={4}>
        <DocumentBackButton onBack={onBack} />

        <DocumentDetailQueryStatus
          isLoading={isLoading}
          isError={isError}
          error={null}
          document={document}
          requirementsTitle={requirementsTitle}
          noRequirementsLabel={noRequirementsLabel}
          officialSourceTitle={officialSourceTitle}
        />
      </VStack>
    </Box>
  );
}

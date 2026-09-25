import { Box, Card, VStack } from "@chakra-ui/react";

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
  document,
  isLoading,
  isError,
  error,
  onRetry,
  onBack,
  requirementsTitle,
  noRequirementsLabel,
  officialSourceTitle,
}: DocumentDetailViewProps) {
  return (
    <Box>
      <VStack align="stretch" gap={4}>
        <DocumentBackButton onBack={onBack} />

        <Card.Root bg="surface.base" borderColor="border">
          <Card.Body>
            <DocumentDetailQueryStatus
              isLoading={isLoading}
              isError={isError}
              error={error}
              onRetry={onRetry}
              document={document}
              requirementsTitle={requirementsTitle}
              noRequirementsLabel={noRequirementsLabel}
              officialSourceTitle={officialSourceTitle}
            />
          </Card.Body>
        </Card.Root>
      </VStack>
    </Box>
  );
}

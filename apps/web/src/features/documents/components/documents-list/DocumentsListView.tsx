import { Box, VStack } from "@chakra-ui/react";

import type { DocumentSummary } from "../../types";
import LocationPicker from "../../../locations/components/location-picker/LocationPicker";

import DocumentsListHeader from "./DocumentsListHeader";
import DocumentsListQueryStatus from "./DocumentsListQueryStatus";

export interface DocumentsListViewProps {
  title: string;
  listTitleLabel: string;
  documents: DocumentSummary[] | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  onMunicipalityChange: (municipalityCode: string | null) => void;
}

export default function DocumentsListView({
  title,
  listTitleLabel,
  documents,
  isLoading,
  isError,
  error,
  onRetry,
  onMunicipalityChange,
}: DocumentsListViewProps) {
  return (
    <Box>
      <DocumentsListHeader title={title} />

      <Box mt={6}>
        <LocationPicker onMunicipalityChange={onMunicipalityChange} />
      </Box>

      <Box mt={6}>
        <VStack align="stretch" gap={3}>
          <DocumentsListQueryStatus
            isLoading={isLoading}
            isError={isError}
            error={error}
            onRetry={onRetry}
            listTitleLabel={listTitleLabel}
            documents={documents}
          />
        </VStack>
      </Box>
    </Box>
  );
}

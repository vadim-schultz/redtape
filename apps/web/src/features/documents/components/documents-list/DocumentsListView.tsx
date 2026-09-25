import { Box, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import type { DocumentSummary } from "../../types";
import LocationPicker from "../../../locations/components/location-picker/LocationPicker";

import DocumentsListHeader from "./DocumentsListHeader";
import DocumentsListQueryStatus from "./DocumentsListQueryStatus";

export interface DocumentsListViewProps {
  title: string;
  filters: ReactNode;
  documents: DocumentSummary[] | undefined;
  isLoading: boolean;
  isRefreshing: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  onMunicipalityChange: (municipalityCode: string | null) => void;
}

export default function DocumentsListView({
  title,
  filters,
  documents,
  isLoading,
  isRefreshing,
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

      <Box mt={6}>{filters}</Box>

      <Box mt={6}>
        <VStack align="stretch" gap={3}>
          <DocumentsListQueryStatus
            isLoading={isLoading}
            isRefreshing={isRefreshing}
            isError={isError}
            error={error}
            onRetry={onRetry}
            documents={documents}
          />
        </VStack>
      </Box>
    </Box>
  );
}

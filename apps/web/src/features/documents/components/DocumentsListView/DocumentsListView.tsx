import { Box, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import type { DocumentSummary } from "../../types";
import { LocationPicker } from "../../../locations/components/LocationPickerView";

import DocumentsListHeader from "./DocumentsListHeader";
import DocumentsListQueryStatus from "./DocumentsListQueryStatus";

export interface DocumentsListViewProps {
  title: string;
  toolbar: {
    filters: ReactNode;
    onMunicipalityChange: (municipalityCode: string | null) => void;
  };
  list: {
    documents: DocumentSummary[] | undefined;
    status: QueryStatus;
  };
}

export default function DocumentsListView({
  title,
  toolbar,
  list,
}: DocumentsListViewProps) {
  return (
    <Box>
      <DocumentsListHeader title={title} />

      <Box mt={6}>
        <LocationPicker onMunicipalityChange={toolbar.onMunicipalityChange} />
      </Box>

      <Box mt={6}>{toolbar.filters}</Box>

      <Box mt={6}>
        <VStack align="stretch" gap={3}>
          <DocumentsListQueryStatus {...list} />
        </VStack>
      </Box>
    </Box>
  );
}

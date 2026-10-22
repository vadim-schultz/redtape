import { Box, VStack } from "@chakra-ui/react";

import type { QueryStatus } from "../../../../components/feedback/queryStatus";

import DocumentBackButton from "./DocumentBackButton";
import DocumentDetailQueryStatus, {
  type DocumentDetailContentData,
} from "./DocumentDetailQueryStatus";

export interface DocumentDetailViewProps {
  status: QueryStatus;
  content: DocumentDetailContentData;
  onBack: () => void;
}

export default function DocumentDetailView({
  status,
  content,
  onBack,
}: DocumentDetailViewProps) {
  return (
    <Box>
      <VStack align="stretch" gap={4}>
        <DocumentBackButton onBack={onBack} />
        <DocumentDetailQueryStatus status={status} content={content} />
      </VStack>
    </Box>
  );
}

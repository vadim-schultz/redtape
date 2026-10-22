import { VStack } from "@chakra-ui/react";

import type { DocumentDetail } from "../../types";

import DocumentSummaryCard from "./DocumentSummaryCard";
import OfficialSourceSection from "./OfficialSourceSection";
import RequirementsSection from "./RequirementsSection";

export interface DocumentDetailContentProps {
  document: DocumentDetail;
  requirementsTitle: string;
  noRequirementsLabel: string;
  officialSourceTitle: string;
}

export default function DocumentDetailContent({
  document,
  requirementsTitle,
  noRequirementsLabel,
  officialSourceTitle,
}: DocumentDetailContentProps) {
  return (
    <VStack align="stretch" gap={6}>
      <DocumentSummaryCard document={document} />
      <RequirementsSection
        document={document}
        requirementsTitle={requirementsTitle}
        noRequirementsLabel={noRequirementsLabel}
      />
      {document.official_url ? (
        <OfficialSourceSection
          url={document.official_url}
          title={officialSourceTitle}
        />
      ) : null}
    </VStack>
  );
}

import { VStack } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import type { DocumentDetail } from "../../types";

import DocumentBreadcrumb from "./DocumentBreadcrumb";
import DocumentHeader from "./DocumentHeader";

export interface DocumentSummaryCardProps {
  document: DocumentDetail;
}

export default function DocumentSummaryCard({
  document,
}: DocumentSummaryCardProps) {
  return (
    <AppCard>
      <VStack align="stretch" gap={3}>
        <DocumentHeader
          title={document.title}
          description={document.description}
          categories={document.categories}
        />
        <DocumentBreadcrumb nodes={document.jurisdiction_path ?? []} />
      </VStack>
    </AppCard>
  );
}

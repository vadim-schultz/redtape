import { Heading, VStack } from "@chakra-ui/react";

import type { DocumentDetail } from "../../types";

import RequirementsEmpty from "./requirements/RequirementsEmpty";
import RequirementsList from "./requirements/RequirementsList";

export interface RequirementsSectionProps {
  document: DocumentDetail;
  requirementsTitle: string;
  noRequirementsLabel: string;
}

/** Heading on the bare canvas, then one card per required document. */
export default function RequirementsSection({
  document,
  requirementsTitle,
  noRequirementsLabel,
}: RequirementsSectionProps) {
  return (
    <VStack align="stretch" gap={3}>
      <Heading textStyle="sectionHeader">{requirementsTitle}</Heading>
      {document.requirements?.length ? (
        <RequirementsList requirements={document.requirements} />
      ) : (
        <RequirementsEmpty label={noRequirementsLabel} />
      )}
    </VStack>
  );
}

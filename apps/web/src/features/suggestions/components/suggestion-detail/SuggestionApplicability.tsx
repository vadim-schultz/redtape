import { Text, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import DocumentBreadcrumb from "../../../documents/components/document-detail/DocumentBreadcrumb";
import type { JurisdictionPathNode } from "../../../documents/types";

export interface SuggestionApplicabilityProps {
  jurisdictionPath: JurisdictionPathNode[];
}

export default function SuggestionApplicability({
  jurisdictionPath,
}: SuggestionApplicabilityProps) {
  const { t } = useLocale();

  if (!jurisdictionPath.length) {
    return null;
  }

  return (
    <VStack align="stretch" gap={1} data-testid="suggestion-applicability">
      <Text textStyle="subsectionHeader">{t("suggestions.applicability")}</Text>
      <DocumentBreadcrumb nodes={jurisdictionPath} />
    </VStack>
  );
}

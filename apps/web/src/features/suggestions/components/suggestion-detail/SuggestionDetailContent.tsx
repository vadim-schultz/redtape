import { VStack } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import type { SuggestionRead } from "../../types";

import EvidenceSection from "../../../evidence/components/EvidenceSection";

import SuggestionApplicability from "./SuggestionApplicability";
import SuggestionDetailHeader from "./SuggestionDetailHeader";
import SuggestionPayloadSection from "./SuggestionPayloadSection";

export interface SuggestionDetailContentProps {
  suggestion: SuggestionRead;
}

export default function SuggestionDetailContent({
  suggestion,
}: SuggestionDetailContentProps) {
  return (
    <VStack align="stretch" gap={6}>
      <AppCard>
        <SuggestionDetailHeader suggestion={suggestion} />
        <SuggestionApplicability
          jurisdictionPath={suggestion.jurisdiction_path ?? []}
        />
      </AppCard>
      <SuggestionPayloadSection suggestion={suggestion} />
      <EvidenceSection suggestionId={suggestion.id} />
    </VStack>
  );
}

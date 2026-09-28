import type { ReactElement } from "react";

import type {
  NewRequirementSuggestionPayload,
  SuggestionKind,
  SuggestionPayload,
  SuggestionRead,
} from "../../types";

import NewDocumentPayloadView from "./NewDocumentPayloadView";
import NewRequirementPayloadView from "./NewRequirementPayloadView";

type PayloadRenderer = (suggestion: SuggestionRead) => ReactElement;

const PAYLOAD_RENDERERS: Record<SuggestionKind, PayloadRenderer> = {
  new_document: (suggestion) => (
    <NewDocumentPayloadView payload={suggestion.payload as SuggestionPayload} />
  ),
  new_requirement: (suggestion) => (
    <NewRequirementPayloadView
      payload={suggestion.payload as NewRequirementSuggestionPayload}
    />
  ),
};

export interface SuggestionPayloadSectionProps {
  suggestion: SuggestionRead;
}

/** One more suggestion kind is one more PAYLOAD_RENDERERS entry, not a branch. */
export default function SuggestionPayloadSection({
  suggestion,
}: SuggestionPayloadSectionProps) {
  return PAYLOAD_RENDERERS[suggestion.kind](suggestion);
}

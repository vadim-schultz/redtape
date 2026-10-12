import { Card, HStack, Text, VStack } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { NewRequirementSuggestionPayload } from "../../types";

export interface NewRequirementPayloadViewProps {
  payload: NewRequirementSuggestionPayload;
}

export default function NewRequirementPayloadView({
  payload,
}: NewRequirementPayloadViewProps) {
  const { t, locale } = useLocale();
  const notes = payload.notes_i18n?.[locale];

  return (
    <VStack align="stretch" gap={3}>
      {notes ? <Text>{notes}</Text> : null}
      <HStack align="stretch" gap={3}>
        <AppCard to={`/documents/${payload.parent_document_id}`}>
          <Card.Title textStyle="subsectionHeader">
            {t("suggestions.parent_document")}
          </Card.Title>
        </AppCard>
        <Text aria-hidden>→</Text>
        <AppCard to={`/documents/${payload.required_document_id}`}>
          <Card.Title textStyle="subsectionHeader">
            {t("suggestions.required_document")}
          </Card.Title>
        </AppCard>
      </HStack>
    </VStack>
  );
}

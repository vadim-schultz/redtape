import { Link, Text, VStack } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { SuggestionPayload } from "../../types";

import SuggestionTaxonomyTags from "./SuggestionTaxonomyTags";

export interface NewDocumentPayloadViewProps {
  payload: SuggestionPayload;
}

export default function NewDocumentPayloadView({
  payload,
}: NewDocumentPayloadViewProps) {
  const { t, locale } = useLocale();
  const description = payload.description_i18n?.[locale];

  return (
    <VStack align="stretch" gap={3}>
      {description ? <Text>{description}</Text> : null}
      <SuggestionTaxonomyTags payload={payload} />
      <AppCard>
        <Text textStyle="subsectionHeader" mb={2}>
          {t("suggestions.official_source")}
        </Text>
        <Link
          href={payload.official_url}
          target="_blank"
          rel="noreferrer"
          color="text.link"
          data-testid="suggestion-official-url"
        >
          {payload.official_url}
        </Link>
      </AppCard>
    </VStack>
  );
}

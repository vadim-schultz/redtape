import { HStack, Text, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { useDomainsQuery } from "../../../taxonomy/hooks/useDomainsQuery";
import { useLifeSituationsQuery } from "../../../taxonomy/hooks/useLifeSituationsQuery";
import type { SuggestionPayload } from "../../types";

export interface SuggestionTaxonomyTagsProps {
  payload: SuggestionPayload;
}

function labelForCode(
  code: string,
  terms: { code: string; name: string }[],
): string {
  return terms.find((term) => term.code === code)?.name ?? code;
}

export default function SuggestionTaxonomyTags({
  payload,
}: SuggestionTaxonomyTagsProps) {
  const { t } = useLocale();
  const domains = useDomainsQuery();
  const situations = useLifeSituationsQuery();

  const domainLabels = payload.domain_codes.map((code) =>
    labelForCode(code, domains.data ?? []),
  );
  const situationLabels = payload.situation_codes.map((code) =>
    labelForCode(code, situations.data ?? []),
  );

  if (!domainLabels.length && !situationLabels.length) {
    return null;
  }

  return (
    <VStack align="stretch" gap={3} data-testid="suggestion-taxonomy">
      {domainLabels.length ? (
        <VStack align="stretch" gap={1}>
          <Text textStyle="subsectionHeader">{t("filters.domain")}</Text>
          <HStack gap={2} flexWrap="wrap">
            {domainLabels.map((label) => (
              <Text key={label} fontSize="sm">
                {label}
              </Text>
            ))}
          </HStack>
        </VStack>
      ) : null}
      {situationLabels.length ? (
        <VStack align="stretch" gap={1}>
          <Text textStyle="subsectionHeader">{t("filters.situation")}</Text>
          <HStack gap={2} flexWrap="wrap">
            {situationLabels.map((label) => (
              <Text key={label} fontSize="sm">
                {label}
              </Text>
            ))}
          </HStack>
        </VStack>
      ) : null}
    </VStack>
  );
}

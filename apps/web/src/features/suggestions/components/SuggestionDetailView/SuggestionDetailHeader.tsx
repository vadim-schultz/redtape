import { Heading, HStack, Text, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { SourceBadge } from "../SuggestionsListView";
import { StatusBadge } from "../SuggestionsListView";
import type { SuggestionRead } from "../../types";
import { formatRelativeTime } from "../../../../utils/relativeTime";
import { suggestionTitle } from "../../utils/suggestionTitle";

export interface SuggestionDetailHeaderProps {
  suggestion: SuggestionRead;
}

export default function SuggestionDetailHeader({
  suggestion,
}: SuggestionDetailHeaderProps) {
  const { t, locale } = useLocale();
  const { display_name } = suggestion.submitted_by;

  return (
    <VStack align="stretch" gap={3}>
      <Heading textStyle="pageTitle">
        {suggestionTitle(suggestion, locale)}
      </Heading>
      <HStack gap={2}>
        <StatusBadge status={suggestion.status} />
        <SourceBadge kind={suggestion.submitted_by.kind} />
        {display_name ? (
          <Text color="muted" fontSize="sm">
            {t("suggestions.submitted_by", { name: display_name })}
          </Text>
        ) : null}
        <Text color="muted" fontSize="sm">
          {formatRelativeTime(suggestion.created_at, locale)}
        </Text>
      </HStack>
    </VStack>
  );
}

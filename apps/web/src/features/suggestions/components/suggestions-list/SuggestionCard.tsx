import { Card, HStack, Text } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { SuggestionRead } from "../../types";
import { formatRelativeTime } from "../../utils/formatRelativeTime";
import { suggestionTitle } from "../../utils/suggestionTitle";

import SourceBadge from "./SourceBadge";
import StatusBadge from "./StatusBadge";

export interface SuggestionCardProps {
  suggestion: SuggestionRead;
  /** Injectable clock so relative-time assertions don't depend on wall-clock time. */
  now?: Date;
}

export default function SuggestionCard({
  suggestion,
  now,
}: SuggestionCardProps) {
  const { locale } = useLocale();

  return (
    <AppCard to={`/suggestions/${suggestion.id}`}>
      <Card.Title textStyle="subsectionHeader">
        {suggestionTitle(suggestion, locale)}
      </Card.Title>
      <HStack mt={2} gap={2}>
        <StatusBadge status={suggestion.status} />
        <SourceBadge kind={suggestion.submitted_by.kind} />
        <Text color="muted" fontSize="sm">
          {formatRelativeTime(suggestion.created_at, locale, now)}
        </Text>
      </HStack>
    </AppCard>
  );
}

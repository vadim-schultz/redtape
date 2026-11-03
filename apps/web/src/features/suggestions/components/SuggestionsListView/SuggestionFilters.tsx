import { HStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { useSuggestionFilters } from "../../hooks/useSuggestionFilters";
import {
  SUGGESTION_STATUS_FILTERS,
  type SuggestionStatusFilter,
} from "../../types";

import StatusFilterChip from "./StatusFilterChip";

function labelKey(status: SuggestionStatusFilter): string {
  return status === "all" ? "filter_all" : `status_${status}`;
}

export default function SuggestionFilters() {
  const { t } = useLocale();
  const filters = useSuggestionFilters();

  return (
    <HStack role="group" aria-label={t("suggestions.list_title")} gap={2}>
      {SUGGESTION_STATUS_FILTERS.map((status) => (
        <StatusFilterChip
          key={status}
          label={t(`suggestions.${labelKey(status)}`)}
          pressed={filters.status === status}
          onSelect={() => filters.setStatus(status)}
        />
      ))}
    </HStack>
  );
}

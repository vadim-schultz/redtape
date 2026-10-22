import { HStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import {
  useSuggestionFilters,
  type SuggestionStatusFilter,
} from "../../hooks/useSuggestionFilters";

import StatusFilterChip from "./StatusFilterChip";

const STATUSES: SuggestionStatusFilter[] = [
  "pending",
  "all",
  "approved",
  "rejected",
];

function labelKey(status: SuggestionStatusFilter): string {
  return status === "all" ? "filter_all" : `status_${status}`;
}

export default function SuggestionFilters() {
  const { t } = useLocale();
  const filters = useSuggestionFilters();

  return (
    <HStack role="group" aria-label={t("suggestions.list_title")} gap={2}>
      {STATUSES.map((status) => (
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

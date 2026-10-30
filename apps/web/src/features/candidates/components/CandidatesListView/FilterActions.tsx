import { Button, HStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateList } from "../../hooks/useCandidateListState";
import { hasActiveFilters } from "../../utils/hasActiveFilters";
import CompleteOnlySwitch from "./CompleteOnlySwitch";

export interface FilterActionsProps {
  list: CandidateList;
}

/** The complete-only switch and, while any filter applies, the clear action. */
export default function FilterActions({ list }: FilterActionsProps) {
  const { t } = useLocale();
  const { state } = list;

  return (
    <HStack gap={4}>
      <CompleteOnlySwitch
        checked={state.filters.complete === "yes"}
        onChange={(on) => list.setFilter("complete", on ? "yes" : undefined)}
      />
      {hasActiveFilters(state) ? (
        <Button size="sm" variant="ghost" onClick={list.clearFilters}>
          {t("candidates.clear_filters")}
        </Button>
      ) : null}
    </HStack>
  );
}

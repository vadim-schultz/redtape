import { Button } from "@chakra-ui/react";
import { LuLayers } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import { useLocale } from "../../../../contexts/LocaleContext";

export interface CandidatesEmptyStateProps {
  /** Present only while filters are active; clears them. */
  onClearFilters: (() => void) | undefined;
}

/** Nothing to show; with filters active it says they hide everything and offers to clear them. */
export default function CandidatesEmptyState({
  onClearFilters,
}: CandidatesEmptyStateProps) {
  const { t } = useLocale();
  const filtered = onClearFilters !== undefined;

  return (
    <EmptyStateCard
      icon={LuLayers}
      content={{
        title: t("candidates.empty_title"),
        description: t(
          filtered
            ? "candidates.empty_filtered_description"
            : "candidates.empty_description",
        ),
        action: filtered ? (
          <Button variant="outline" onClick={onClearFilters}>
            {t("candidates.clear_filters")}
          </Button>
        ) : undefined,
      }}
    />
  );
}

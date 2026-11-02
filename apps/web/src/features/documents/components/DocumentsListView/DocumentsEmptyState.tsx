import { Button } from "@chakra-ui/react";
import { LuFileSearch } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import { useLocale } from "../../../../contexts/LocaleContext";

export interface DocumentsEmptyStateProps {
  /** Present only while chips or a search narrow the list; clears them. */
  onClearFilters: (() => void) | undefined;
}

/** Nothing to show; when chips or a search narrow the list it says so and offers to clear them. */
export default function DocumentsEmptyState({
  onClearFilters,
}: DocumentsEmptyStateProps) {
  const { t } = useLocale();
  const filtered = onClearFilters !== undefined;

  return (
    <EmptyStateCard
      icon={LuFileSearch}
      content={{
        title: t("documents.empty_title"),
        description: t(
          filtered
            ? "documents.empty_filtered_description"
            : "documents.empty_description",
        ),
        action: filtered ? (
          <Button variant="outline" onClick={onClearFilters}>
            {t("filters.clear")}
          </Button>
        ) : undefined,
      }}
    />
  );
}

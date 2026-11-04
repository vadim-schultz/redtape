import { Button, Text, VStack } from "@chakra-ui/react";

import QueryError from "../../../../../components/feedback/QueryError";
import { useLocale } from "../../../../../contexts/LocaleContext";
import type { DocumentFilters as DocumentFiltersState } from "../../../hooks/useDocumentFilters";
import type { FilterTaxonomy } from "../../../hooks/useFilterTaxonomy";

import { hasSelectedChips } from "../../../utils/hasSelectedChips";
import CategoryFilterView from "./CategoryFilterView";

export interface DocumentFiltersProps {
  taxonomy: FilterTaxonomy;
  filters: DocumentFiltersState;
}

export default function DocumentFilters({
  taxonomy,
  filters,
}: DocumentFiltersProps) {
  const { t } = useLocale();

  if (taxonomy.isError) return <QueryError onRetry={taxonomy.onRetry} />;

  return (
    <VStack align="stretch" gap={4}>
      <Text textStyle="subsectionHeader">{t("filters.category")}</Text>
      <CategoryFilterView
        categories={taxonomy.categories}
        filters={filters}
      />
      {hasSelectedChips(filters) ? (
        <Button alignSelf="start" variant="ghost" onClick={filters.clear}>
          {t("filters.clear")}
        </Button>
      ) : null}
    </VStack>
  );
}

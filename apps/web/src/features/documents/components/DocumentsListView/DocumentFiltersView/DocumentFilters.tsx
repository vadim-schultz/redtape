import { Button, VStack } from "@chakra-ui/react";

import QueryError from "../../../../../components/feedback/QueryError";
import { useLocale } from "../../../../../contexts/LocaleContext";
import type { DocumentFilters as DocumentFiltersState } from "../../../hooks/useDocumentFilters";
import type { FilterTaxonomy } from "../../../hooks/useFilterTaxonomy";

import FilterGroup from "./FilterGroup";

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

  const hasFilters = filters.domains.length + filters.situations.length > 0;

  return (
    <VStack align="stretch" gap={4}>
      <FilterGroup
        heading={t("filters.domain")}
        terms={taxonomy.domains}
        selected={filters.domains}
        onToggle={filters.toggleDomain}
      />
      <FilterGroup
        heading={t("filters.situation")}
        terms={taxonomy.situations}
        selected={filters.situations}
        onToggle={filters.toggleSituation}
      />
      {hasFilters ? (
        <Button alignSelf="start" variant="ghost" onClick={filters.clear}>
          {t("filters.clear")}
        </Button>
      ) : null}
    </VStack>
  );
}

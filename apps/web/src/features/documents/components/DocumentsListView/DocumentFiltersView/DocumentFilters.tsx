import { Button, Text, VStack } from "@chakra-ui/react";

import QueryError from "../../../../../components/feedback/QueryError";
import { useLocale } from "../../../../../contexts/LocaleContext";
import type { DocumentFilters as DocumentFiltersState } from "../../../hooks/useDocumentFilters";
import type { FilterTaxonomy } from "../../../hooks/useFilterTaxonomy";

import FilterGroup from "./FilterGroup";
import { LeafFacet, SituationFilterView } from "./SituationFilterView";

export interface DocumentFiltersProps {
  taxonomy: FilterTaxonomy;
  filters: DocumentFiltersState;
  availableLeafCodes?: string[];
}

export default function DocumentFilters({
  taxonomy,
  filters,
  availableLeafCodes = [],
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
      <VStack align="stretch" gap={2}>
        <Text textStyle="subsectionHeader">{t("filters.situation")}</Text>
        <SituationFilterView
          groups={taxonomy.groups}
          situations={taxonomy.situations}
          filters={filters}
        />
        <LeafFacet
          codes={availableLeafCodes}
          selected={filters.leaves}
          onToggle={filters.toggleLeaf}
        />
      </VStack>
      {hasFilters ? (
        <Button alignSelf="start" variant="ghost" onClick={filters.clear}>
          {t("filters.clear")}
        </Button>
      ) : null}
    </VStack>
  );
}

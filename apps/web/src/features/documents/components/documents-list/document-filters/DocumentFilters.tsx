import { Button, VStack } from "@chakra-ui/react";

import QueryError from "../../../../../components/feedback/QueryError";
import { useLocale } from "../../../../../contexts/LocaleContext";
import { useDomainsQuery } from "../../../../taxonomy/hooks/useDomainsQuery";
import { useLifeSituationsQuery } from "../../../../taxonomy/hooks/useLifeSituationsQuery";
import { useDocumentFilters } from "../../../hooks/useDocumentFilters";

import FilterGroup from "./FilterGroup";

export default function DocumentFilters() {
  const { t } = useLocale();
  const filters = useDocumentFilters();
  const domains = useDomainsQuery();
  const situations = useLifeSituationsQuery();

  if (domains.isError || situations.isError) {
    return (
      <QueryError
        onRetry={() => {
          void domains.refetch();
          void situations.refetch();
        }}
      />
    );
  }

  const hasFilters = filters.domains.length + filters.situations.length > 0;

  return (
    <VStack align="stretch" gap={4}>
      <FilterGroup
        heading={t("filters.domain")}
        terms={domains.data ?? []}
        selected={filters.domains}
        onToggle={filters.toggleDomain}
      />
      <FilterGroup
        heading={t("filters.situation")}
        terms={situations.data ?? []}
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

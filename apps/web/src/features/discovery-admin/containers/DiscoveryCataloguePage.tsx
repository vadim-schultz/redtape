import { Stack, Text } from "@chakra-ui/react";

import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";
import DiscoveryCatalogueQueryStatus from "../components/DiscoveryCatalogueQueryStatus";
import type { DiscoveryCatalogueQueryState } from "../components/DiscoveryCatalogueQueryStatus";
import CatalogueServicesTable from "../components/CatalogueServicesTable";
import CoverageChips from "../components/CoverageChips";
import { useDiscoveryCatalogueQuery } from "../hooks/useDiscoveryCatalogueQuery";
import { useDiscoveryCoverageQuery } from "../hooks/useDiscoveryCoverageQuery";

function queryStateFor(
  isPending: boolean,
  isError: boolean,
  hasData: boolean,
): DiscoveryCatalogueQueryState {
  if (isPending) return "loading";
  if (isError || !hasData) return "error";
  return "ready";
}

/** Imported catalogue index at ``/admin/discovery/catalogue``. */
export default function DiscoveryCataloguePage() {
  const { t } = useLocale();
  const coverageQuery = useDiscoveryCoverageQuery();
  const catalogueQuery = useDiscoveryCatalogueQuery();
  const coverageState = queryStateFor(
    coverageQuery.isPending,
    coverageQuery.isError,
    Boolean(coverageQuery.data),
  );
  const catalogueState = queryStateFor(
    catalogueQuery.isPending,
    catalogueQuery.isError,
    Boolean(catalogueQuery.data),
  );

  if (coverageState === "loading" && catalogueState === "loading") {
    return (
      <Text role="status" aria-label={t("common.loading")}>
        {t("common.loading")}
      </Text>
    );
  }

  if (coverageState === "error" && catalogueState === "error") {
    return (
      <QueryError
        onRetry={() => {
          void coverageQuery.refetch();
          void catalogueQuery.refetch();
        }}
      />
    );
  }

  return (
    <Stack gap={4} align="stretch">
      <DiscoveryCatalogueQueryStatus
        state={coverageState}
        onRetry={() => void coverageQuery.refetch()}
      >
        <CoverageChips coverage={coverageQuery.data!} />
      </DiscoveryCatalogueQueryStatus>
      <DiscoveryCatalogueQueryStatus
        state={catalogueState}
        onRetry={() => void catalogueQuery.refetch()}
      >
        <CatalogueServicesTable items={catalogueQuery.data?.items ?? []} />
      </DiscoveryCatalogueQueryStatus>
    </Stack>
  );
}

import { Spinner, Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import CatalogueServicesTable from "../components/CatalogueServicesTable";
import CoverageChips from "../components/CoverageChips";
import { useDiscoveryCatalogueQuery } from "../hooks/useDiscoveryCatalogueQuery";
import { useDiscoveryCoverageQuery } from "../hooks/useDiscoveryCoverageQuery";

/** Imported catalogue index at ``/admin/discovery/catalogue``. */
export default function DiscoveryCataloguePage() {
  const { t } = useLocale();
  const coverageQuery = useDiscoveryCoverageQuery();
  const catalogueQuery = useDiscoveryCatalogueQuery();

  const isLoading = coverageQuery.isLoading || catalogueQuery.isLoading;
  const isError = coverageQuery.isError || catalogueQuery.isError;

  if (isLoading) {
    return <Spinner />;
  }

  if (isError || !coverageQuery.data) {
    return (
      <Text color="fg.error">{t("discovery_admin.catalogue.load_error")}</Text>
    );
  }

  return (
    <Stack gap={4} align="stretch">
      <CoverageChips coverage={coverageQuery.data} />
      <CatalogueServicesTable items={catalogueQuery.data?.items ?? []} />
    </Stack>
  );
}

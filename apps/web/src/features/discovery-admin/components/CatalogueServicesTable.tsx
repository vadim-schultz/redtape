import { Text } from "@chakra-ui/react";

import { DataTable } from "../../../components/data-display/DataTable";
import { useLocale } from "../../../contexts/LocaleContext";
import type { CatalogueServiceSummary } from "../types";
import {
  catalogueColumns,
  cataloguePipelineHref,
} from "./columns/catalogueColumns";

export interface CatalogueServicesTableProps {
  items: CatalogueServiceSummary[];
}

/** Catalogue index in the shared table, each row linking to its pipeline drill-down. */
export default function CatalogueServicesTable({
  items,
}: CatalogueServicesTableProps) {
  const locale = useLocale();

  return (
    <DataTable
      label={locale.t("discovery_admin.catalogue.table_label")}
      columns={catalogueColumns(locale)}
      rows={{
        items,
        getKey: (row) => row.id,
        getHref: cataloguePipelineHref,
      }}
      states={{
        empty: <Text>{locale.t("discovery_admin.catalogue.empty")}</Text>,
      }}
    />
  );
}

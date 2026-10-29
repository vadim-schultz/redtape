import { Stack } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { CatalogueList } from "../hooks/useCatalogueListState";
import type { CataloguePanel } from "../hooks/useCatalogueState";
import CatalogueServicesTable from "./CatalogueServicesTable";
import ListSearch from "./ListSearch";

export interface CatalogueIndexPanelProps {
  panel: CataloguePanel;
  list: CatalogueList;
}

/** External-id search above the catalogue table, whose header carries sort and the source filter. */
export default function CatalogueIndexPanel({
  panel,
  list,
}: CatalogueIndexPanelProps) {
  const { t } = useLocale();

  return (
    <Stack gap={4} align="stretch">
      <ListSearch
        value={list.state.search}
        label={t("discovery_admin.catalogue.filter_search")}
        onSearch={list.setSearch}
      />
      <CatalogueServicesTable
        page={panel.page}
        status={panel.status}
        list={list}
      />
    </Stack>
  );
}

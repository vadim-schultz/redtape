import { Stack } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { CatalogueList } from "../hooks/useCatalogueListState";
import type { CataloguePanel } from "../hooks/useCatalogueState";
import CatalogueServicesTable from "./CatalogueServicesTable";
import CatalogueSummaryChips from "./CatalogueSummaryChips";
import ListSearch from "./ListSearch";

export interface CatalogueIndexPanelProps {
  panel: CataloguePanel;
  list: CatalogueList;
}

/** Summary chips and external-id search above the catalogue table, whose header carries sort and the column filters. */
export default function CatalogueIndexPanel({
  panel,
  list,
}: CatalogueIndexPanelProps) {
  const { t } = useLocale();

  return (
    <Stack gap={4} align="stretch">
      {panel.page ? (
        <CatalogueSummaryChips summary={panel.page.summary} list={list} />
      ) : null}
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

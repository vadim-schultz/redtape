import { Stack } from "@chakra-ui/react";

import ListSearchBox from "../../../components/data-display/ListSearchBox";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { CatalogueList } from "../types/listControllers";
import type { CatalogueListResponse } from "../types";
import CatalogueServicesTable from "./CatalogueServicesTable";
import CatalogueSummaryChips from "./CatalogueSummaryChips";

export interface CatalogueIndexPanelProps {
  page: CatalogueListResponse | undefined;
  status: QueryStatus;
  list: CatalogueList;
}

/** Summary chips and external-id search above the catalogue table, whose header carries sort and the column filters. */
export default function CatalogueIndexPanel({
  page,
  status,
  list,
}: CatalogueIndexPanelProps) {
  const { t } = useLocale();

  return (
    <Stack gap={4} align="stretch">
      {page ? (
        <CatalogueSummaryChips summary={page.summary} list={list} />
      ) : null}
      <ListSearchBox
        value={list.state.search}
        copy={{ label: t("discovery_admin.catalogue.filter_search") }}
        onSearch={list.setSearch}
      />
      <CatalogueServicesTable page={page} status={status} list={list} />
    </Stack>
  );
}

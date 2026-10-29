import { LuLibrary } from "react-icons/lu";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import { toTableQuery } from "../../../hooks/toTableQuery";
import type { CatalogueList } from "../hooks/useCatalogueListState";
import type { CatalogueListResponse } from "../types";
import {
  catalogueColumns,
  cataloguePipelineHref,
} from "./columns/catalogueColumns";
import DiscoveryDataTable from "./DiscoveryDataTable";

const NAMESPACE = "discovery_admin.catalogue";
const COPY = { namespace: NAMESPACE, icon: LuLibrary };

export interface CatalogueServicesTableProps {
  page: CatalogueListResponse | undefined;
  status: QueryStatus;
  list: CatalogueList;
}

/** Catalogue index in the shared table: header sort and source filter, response total, server paging and a link to each pipeline. */
export default function CatalogueServicesTable({
  page,
  status,
  list,
}: CatalogueServicesTableProps) {
  const locale = useLocale();

  return (
    <DiscoveryDataTable
      table={{
        label: locale.t(`${NAMESPACE}.table_label`),
        columns: catalogueColumns(locale),
        getKey: (row) => row.id,
        getHref: cataloguePipelineHref,
        query: toTableQuery(list),
      }}
      page={page}
      status={status}
      onOffsetChange={list.setOffset}
      copy={COPY}
    />
  );
}

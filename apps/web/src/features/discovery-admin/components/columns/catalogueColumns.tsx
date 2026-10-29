import { Link } from "react-router-dom";

import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import { DISCOVERY_SOURCES } from "../../types/listValues";
import type {
  CatalogueFilterKey,
  CatalogueServiceSummary,
  CatalogueSortKey,
} from "../../types";
import { headerLabels, type ColumnContext } from "./columnContext";
import { plainOptions } from "./filterOptions";

export type CatalogueColumn = DataTableColumn<
  CatalogueServiceSummary,
  CatalogueSortKey,
  CatalogueFilterKey
>;

/** Where a catalogue row's pipeline drill-down lives. */
export const cataloguePipelineHref = (service: CatalogueServiceSummary) =>
  `/admin/discovery/pipeline/${service.id}`;

/** Columns of the catalogue index; the external id links to the pipeline. */
export function catalogueColumns(context: ColumnContext): CatalogueColumn[] {
  const header = headerLabels(context, "discovery_admin.catalogue");
  return [
    {
      key: "external_id",
      header: header("external_id"),
      canSort: "external_id",
      render: (row) => (
        <Link to={cataloguePipelineHref(row)}>{row.external_id}</Link>
      ),
    },
    {
      key: "source",
      header: header("source"),
      canSort: "source",
      filter: {
        key: "source",
        operators: ["eq"],
        label: context.t("discovery_admin.catalogue.filter_source"),
        options: plainOptions(DISCOVERY_SOURCES),
      },
      render: (row) => row.source,
    },
    {
      key: "stage",
      header: header("stage"),
      canSort: "stage",
      render: (row) => row.pipeline_stage,
    },
  ];
}

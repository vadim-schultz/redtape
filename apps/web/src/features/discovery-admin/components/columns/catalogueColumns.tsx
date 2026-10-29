import { Link } from "react-router-dom";

import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import type { CatalogueServiceSummary } from "../../types";
import { headerLabels, type ColumnContext } from "./columnContext";

/** The catalogue API has no sort or filter contract yet, so no catalogue column declares one. */
export type CatalogueColumn = DataTableColumn<
  CatalogueServiceSummary,
  never,
  never
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
      render: (row) => (
        <Link to={cataloguePipelineHref(row)}>{row.external_id}</Link>
      ),
    },
    { key: "source", header: header("source"), render: (row) => row.source },
    {
      key: "stage",
      header: header("stage"),
      render: (row) => row.pipeline_stage,
    },
  ];
}

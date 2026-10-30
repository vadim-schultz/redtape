import { Link } from "react-router-dom";

import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import TruncatedText from "../../../../components/data-display/TruncatedText";
import { DISCOVERY_SOURCES, PIPELINE_STAGES } from "../../types/listValues";
import type {
  CatalogueFilterKey,
  CatalogueServiceSummary,
  CatalogueSortKey,
} from "../../types";
import { localizedTitle } from "../../utils/localizedTitle";
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

/** Width at which the title column clips its text. */
const TITLE_MAX_WIDTH = "28rem";

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
      key: "title",
      header: header("title"),
      canSort: "title",
      maxWidth: TITLE_MAX_WIDTH,
      render: (row) => (
        <TruncatedText maxWidth={TITLE_MAX_WIDTH}>
          {localizedTitle(row.title_i18n, context.locale) || row.external_id}
        </TruncatedText>
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
      filter: {
        key: "stage",
        operators: ["eq"],
        label: context.t("discovery_admin.catalogue.filter_stage"),
        options: plainOptions(PIPELINE_STAGES),
      },
      render: (row) => row.pipeline_stage,
    },
  ];
}

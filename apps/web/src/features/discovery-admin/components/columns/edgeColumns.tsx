import { Badge } from "@chakra-ui/react";
import { Link } from "react-router-dom";

import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import type { DiscoveryCandidateEdge } from "../../types";
import { localizedTitle } from "../../utils/localizedTitle";
import { translateOrRaw } from "../../utils/translateOrRaw";
import EdgeConditionCell from "./cells/EdgeConditionCell";
import { headerLabels, type ColumnContext } from "./columnContext";

/** Which end of the edge the table shows: the document it requires, or the document that requires this one. */
export type EdgeEnd = "required" | "parent";

/** Staged edges are read-only: no column declares a sort or filter. */
export type EdgeColumn = DataTableColumn<DiscoveryCandidateEdge, never, never>;

function otherEnd(edge: DiscoveryCandidateEdge, end: EdgeEnd) {
  return end === "required"
    ? { id: edge.required_candidate_id, title: edge.required_title_i18n }
    : { id: edge.parent_candidate_id, title: edge.parent_title_i18n };
}

/** Columns of an edge table: the other document, condition, basis and the stating procedure. */
export function edgeColumns(
  context: ColumnContext,
  end: EdgeEnd,
): EdgeColumn[] {
  const { locale, t } = context;
  const header = headerLabels(context, "discovery_admin.document.edges");
  return [
    {
      key: "document",
      header: header("document"),
      render: (edge) => {
        const other = otherEnd(edge, end);
        return (
          <Link to={`/admin/discovery/documents/${other.id}`}>
            {localizedTitle(other.title, locale) || other.id}
          </Link>
        );
      },
    },
    {
      key: "condition",
      header: t("discovery_admin.document.col_condition"),
      render: (edge) => <EdgeConditionCell edge={edge} />,
    },
    {
      key: "basis",
      header: header("basis"),
      render: (edge) => (
        <Badge variant="subtle" colorPalette="purple">
          {translateOrRaw(
            t,
            `discovery_admin.document.edges.basis_${edge.basis}`,
            edge.basis,
          )}
        </Badge>
      ),
    },
    {
      key: "procedure",
      header: t("discovery_admin.document.edges.procedure"),
      render: (edge) => (
        <Link to={`/admin/discovery/pipeline/${edge.catalogue_service_id}`}>
          {localizedTitle(edge.procedure_title_i18n, locale) ||
            edge.catalogue_service_id}
        </Link>
      ),
    },
  ];
}

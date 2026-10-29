import { Link } from "react-router-dom";

import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import { formatRelativeTime } from "../../../suggestions/utils/formatRelativeTime";
import type {
  CandidateFilterKey,
  CandidateSortKey,
  DiscoveryCandidate,
} from "../../types";
import { localizedTitle } from "../../utils/localizedTitle";
import { candidateHref } from "./candidateRows";
import CandidateRolesCell from "./cells/CandidateRolesCell";
import { headerLabels, type ColumnContext } from "./columnContext";

export type CandidateColumn = DataTableColumn<
  DiscoveryCandidate,
  CandidateSortKey,
  CandidateFilterKey
>;

/** Columns of the documents list; only title, mentions and first-seen declare a sort the API supports. */
export function candidateColumns(context: ColumnContext): CandidateColumn[] {
  const { locale } = context;
  const header = headerLabels(context, "discovery_admin.documents");
  return [
    {
      key: "title",
      header: header("title"),
      canSort: "title",
      render: (c) => (
        <Link to={candidateHref(c)}>
          {localizedTitle(c.title_i18n, locale) || c.key}
        </Link>
      ),
    },
    {
      key: "jurisdiction",
      header: header("jurisdiction"),
      render: (c) => localizedTitle(c.jurisdiction_name_i18n, locale) || "—",
    },
    {
      key: "roles",
      header: header("roles"),
      render: (c) => <CandidateRolesCell candidate={c} />,
    },
    {
      key: "mentions",
      header: header("mentions"),
      canSort: "mentions",
      render: (c) => c.mention_count,
    },
    { key: "status", header: header("status"), render: (c) => c.status },
    {
      key: "first_seen",
      header: header("first_seen"),
      canSort: "created_at",
      render: (c) => formatRelativeTime(c.created_at, locale),
    },
  ];
}

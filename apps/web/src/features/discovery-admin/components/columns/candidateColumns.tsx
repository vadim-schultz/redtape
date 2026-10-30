import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import { formatRelativeTime } from "../../../suggestions/utils/formatRelativeTime";
import type {
  CandidateFilterKey,
  CandidateSortKey,
  DiscoveryCandidate,
} from "../../types";
import { localizedTitle } from "../../utils/localizedTitle";
import CandidateReadinessCell from "./cells/CandidateReadinessCell";
import CandidateRolesCell from "./cells/CandidateRolesCell";
import CandidateTitleCell, {
  TITLE_MAX_WIDTH,
} from "./cells/CandidateTitleCell";
import { candidateFilters } from "./candidateFilters";
import { headerLabels, type ColumnContext } from "./columnContext";

export type CandidateColumn = DataTableColumn<
  DiscoveryCandidate,
  CandidateSortKey,
  CandidateFilterKey
>;

/**
 * Columns of the documents list. Every column sorts; roles, mentions, status
 * and readiness filter. Title and first-seen filter nowhere: free text is the
 * search box, and a date range is not offered.
 */
export function candidateColumns(context: ColumnContext): CandidateColumn[] {
  const { locale, t } = context;
  const header = headerLabels(context, "discovery_admin.documents");
  const filter = candidateFilters(t);
  return [
    {
      key: "title",
      header: header("title"),
      canSort: "title",
      maxWidth: TITLE_MAX_WIDTH,
      render: (c) => <CandidateTitleCell candidate={c} locale={locale} />,
    },
    {
      key: "jurisdiction",
      header: header("jurisdiction"),
      canSort: "jurisdiction",
      render: (c) => localizedTitle(c.jurisdiction_name_i18n, locale) || "—",
    },
    {
      key: "roles",
      header: header("roles"),
      canSort: "roles",
      filter: filter.roles,
      render: (c) => <CandidateRolesCell candidate={c} />,
    },
    {
      key: "mentions",
      header: header("mentions"),
      align: "end",
      canSort: "mentions",
      filter: filter.mentions,
      render: (c) => c.mention_count,
    },
    {
      key: "status",
      header: header("status"),
      canSort: "status",
      filter: filter.status,
      render: (c) => c.status,
    },
    {
      key: "readiness",
      header: header("readiness"),
      canSort: "completeness",
      filter: filter.readiness,
      render: (c) => <CandidateReadinessCell candidate={c} />,
    },
    {
      key: "first_seen",
      header: header("first_seen"),
      canSort: "created_at",
      render: (c) => formatRelativeTime(c.created_at, locale),
    },
  ];
}

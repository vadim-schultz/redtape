import { Link } from "react-router-dom";

import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import type { DiscoveryCandidateMention } from "../../types";
import { hostOf } from "../../utils/hostOf";
import { localizedTitle } from "../../utils/localizedTitle";
import MentionRoleCell from "./cells/MentionRoleCell";
import { headerLabels, type ColumnContext } from "./columnContext";
import LongText from "./LongText";

/**
 * Mentions are one candidate's complete evidence set, embedded in its detail
 * response in a fixed oldest-first order with no paging, so there is no server
 * operation to push a sort or filter to; no column declares one.
 */
export type MentionColumn = DataTableColumn<
  DiscoveryCandidateMention,
  never,
  never
>;

/** Columns of a document's mentions: role, excerpt, condition, extractor and the stating procedure. */
export function mentionColumns(context: ColumnContext): MentionColumn[] {
  const { locale } = context;
  const header = headerLabels(context, "discovery_admin.document");
  return [
    {
      key: "role",
      header: header("role"),
      render: (m) => <MentionRoleCell mention={m} />,
    },
    {
      key: "excerpt",
      header: header("excerpt"),
      render: (m) => <LongText>{m.excerpt}</LongText>,
    },
    {
      key: "condition",
      header: header("condition"),
      render: (m) => <LongText>{m.condition ?? "—"}</LongText>,
    },
    { key: "field", header: header("field"), render: (m) => m.source_field },
    {
      key: "extractor",
      header: header("extractor"),
      render: (m) => `${m.extractor}@${m.extractor_version}`,
    },
    {
      key: "host",
      header: header("host"),
      render: (m) => hostOf(m.portal_url) || "—",
    },
    {
      key: "procedure",
      header: header("procedure"),
      render: (m) => (
        <Link to={`/admin/discovery/pipeline/${m.catalogue_service_id}`}>
          {localizedTitle(m.procedure_title_i18n, locale) ||
            m.catalogue_service_id}
        </Link>
      ),
    },
  ];
}

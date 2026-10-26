import { Table } from "@chakra-ui/react";
import { Link } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";
import { formatRelativeTime } from "../../suggestions/utils/formatRelativeTime";
import type { DiscoveryCandidate } from "../types";
import { localizedTitle } from "../utils/localizedTitle";

const COLUMNS = [
  "title",
  "jurisdiction",
  "roles",
  "mentions",
  "status",
  "first_seen",
];

const NAMESPACE = "discovery_admin.documents";

/** Candidate rows with a link to the document detail route. */
export default function DiscoveryDocumentsTable({
  candidates,
}: {
  candidates: DiscoveryCandidate[];
}) {
  const { locale, t } = useLocale();
  const roles = (candidate: DiscoveryCandidate) =>
    candidate.roles.map((role) => t(`${NAMESPACE}.role_${role}`)).join(", ");

  return (
    <Table.Root size="sm" variant="line">
      <Table.Header>
        <Table.Row>
          {COLUMNS.map((column) => (
            <Table.ColumnHeader key={column}>
              {t(`${NAMESPACE}.col_${column}`)}
            </Table.ColumnHeader>
          ))}
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {candidates.map((candidate) => (
          <Table.Row key={candidate.id}>
            <Table.Cell>
              <Link to={`/admin/discovery/documents/${candidate.id}`}>
                {localizedTitle(candidate.title_i18n, locale) || candidate.key}
              </Link>
            </Table.Cell>
            <Table.Cell>
              {localizedTitle(candidate.jurisdiction_name_i18n, locale) || "—"}
            </Table.Cell>
            <Table.Cell>{roles(candidate)}</Table.Cell>
            <Table.Cell>{candidate.mention_count}</Table.Cell>
            <Table.Cell>{candidate.status}</Table.Cell>
            <Table.Cell>
              {formatRelativeTime(candidate.created_at, locale)}
            </Table.Cell>
          </Table.Row>
        ))}
      </Table.Body>
    </Table.Root>
  );
}

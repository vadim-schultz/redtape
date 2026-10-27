import { Box, Table, Text } from "@chakra-ui/react";
import { Link } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCandidateMention } from "../types";
import { hostOf } from "../utils/hostOf";
import { localizedTitle } from "../utils/localizedTitle";
import MentionRoleChip from "./MentionRoleChip";

const COLUMNS = ["role", "excerpt", "field", "extractor", "host", "procedure"];
const NAMESPACE = "discovery_admin.document";

function MentionRow({ mention }: { mention: DiscoveryCandidateMention }) {
  const { locale } = useLocale();
  const title = localizedTitle(mention.procedure_title_i18n, locale);

  return (
    <Table.Row>
      <Table.Cell>
        <MentionRoleChip role={mention.role} />
      </Table.Cell>
      <Table.Cell whiteSpace="normal">{mention.excerpt}</Table.Cell>
      <Table.Cell>{mention.source_field}</Table.Cell>
      <Table.Cell>{`${mention.extractor}@${mention.extractor_version}`}</Table.Cell>
      <Table.Cell>{hostOf(mention.portal_url) || "—"}</Table.Cell>
      <Table.Cell>
        <Link to={`/admin/discovery/pipeline/${mention.catalogue_service_id}`}>
          {title || mention.catalogue_service_id}
        </Link>
      </Table.Cell>
    </Table.Row>
  );
}

/** Where a document was found: one row per mention with its excerpt and procedure link. */
export default function DocumentMentionsTable({
  mentions,
}: {
  mentions: DiscoveryCandidateMention[];
}) {
  const { t } = useLocale();

  if (mentions.length === 0) {
    return (
      <Text fontSize="sm" color="muted">
        {t(`${NAMESPACE}.mentions_empty`)}
      </Text>
    );
  }

  return (
    <Box overflowX="auto">
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
          {mentions.map((mention) => (
            <MentionRow key={mention.id} mention={mention} />
          ))}
        </Table.Body>
      </Table.Root>
    </Box>
  );
}

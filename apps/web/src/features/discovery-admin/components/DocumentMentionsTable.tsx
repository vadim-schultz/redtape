import { Text } from "@chakra-ui/react";

import { DataTable } from "../../../components/data-display/DataTable";
import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCandidateMention } from "../types";
import { mentionColumns } from "./columns/mentionColumns";

const NAMESPACE = "discovery_admin.document";

/** Where a document was found: one row per mention with its excerpt and procedure link. */
export default function DocumentMentionsTable({
  mentions,
}: {
  mentions: DiscoveryCandidateMention[];
}) {
  const locale = useLocale();

  return (
    <DataTable
      label={locale.t(`${NAMESPACE}.mentions_title`)}
      columns={mentionColumns(locale)}
      rows={{ items: mentions, getKey: (mention) => mention.id }}
      states={{
        empty: (
          <Text textStyle="caption" color="muted">
            {locale.t(`${NAMESPACE}.mentions_empty`)}
          </Text>
        ),
      }}
    />
  );
}

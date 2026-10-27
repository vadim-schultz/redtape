import { HStack, Link, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryArtifact } from "../types";
import { formatBytes } from "../utils/formatBytes";
import { formatDate } from "../utils/formatDate";
import { hostOf } from "../utils/hostOf";

/** One stored page: size, fetch date, final host and a download link; the content is never rendered. */
export default function SnapshotRow({
  artifact,
}: {
  artifact: DiscoveryArtifact;
}) {
  const { locale, t } = useLocale();
  const meta = t("discovery_admin.artifacts.html_meta", {
    size: formatBytes(artifact.byte_size, locale),
    date: formatDate(artifact.fetched_at, locale),
    host: hostOf(artifact.final_url ?? artifact.source_url),
  });

  return (
    <HStack gap={3} fontSize="sm">
      <Text>{meta}</Text>
      {artifact.url === null ? (
        <Text color="muted">
          {t("discovery_admin.artifacts.link_unavailable")}
        </Text>
      ) : (
        <Link href={artifact.url} rel="noopener noreferrer">
          {t("discovery_admin.artifacts.download")}
        </Link>
      )}
    </HStack>
  );
}

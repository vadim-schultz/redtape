import { Link, Text } from "@chakra-ui/react";

import { useLocale } from "../../../../../contexts/LocaleContext";
import type { DiscoveryArtifact } from "../../../types";

/** The download link of a stored page; the content itself is never rendered. */
export default function SnapshotDownloadCell({
  artifact,
}: {
  artifact: DiscoveryArtifact;
}) {
  const { t } = useLocale();
  if (artifact.url === null) {
    return (
      <Text color="muted">
        {t("discovery_admin.artifacts.link_unavailable")}
      </Text>
    );
  }
  return (
    <Link href={artifact.url} rel="noopener noreferrer">
      {t("discovery_admin.artifacts.download")}
    </Link>
  );
}

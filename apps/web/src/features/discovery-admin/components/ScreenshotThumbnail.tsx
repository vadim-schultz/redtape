import { Image, Link, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryArtifact } from "../types";
import { formatDate } from "../../../utils/format/formatDate";

/** A lazy thumbnail linking to the full image in a new tab; the URL stays an opaque string. */
export default function ScreenshotThumbnail({
  artifact,
}: {
  artifact: DiscoveryArtifact;
}) {
  const { locale, t } = useLocale();
  const alt = t("discovery_admin.artifacts.screenshot_alt", {
    date: formatDate(artifact.fetched_at, locale),
  });

  if (artifact.url === null) {
    return (
      <Text fontSize="sm" color="muted">
        {t("discovery_admin.artifacts.link_unavailable")}
      </Text>
    );
  }

  return (
    <Link href={artifact.url} target="_blank" rel="noopener noreferrer">
      <Image
        src={artifact.url}
        alt={alt}
        loading="lazy"
        maxH="10rem"
        borderWidth="1px"
        borderRadius="md"
      />
    </Link>
  );
}

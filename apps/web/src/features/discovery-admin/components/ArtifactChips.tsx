import { Badge, WrapItem } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryArtifactCoverage } from "../types";
import { formatBytes } from "../utils/formatBytes";
import { nearsStorageCap } from "../utils/nearsStorageCap";
import { translateOrRaw } from "../utils/translateOrRaw";

export interface ArtifactChipsProps {
  artifacts: DiscoveryArtifactCoverage;
}

function StorageChip({ artifacts }: ArtifactChipsProps) {
  const { locale, t } = useLocale();
  const nearlyFull = nearsStorageCap(
    artifacts.total_bytes,
    artifacts.bytes_cap,
  );
  const key = nearlyFull ? "chip_total_warning" : "chip_total";

  return (
    <WrapItem>
      <Badge variant="subtle" colorPalette={nearlyFull ? "orange" : "teal"}>
        {t(`discovery_admin.artifacts.${key}`, {
          size: formatBytes(artifacts.total_bytes, locale),
          cap: formatBytes(artifacts.bytes_cap, locale),
        })}
      </Badge>
    </WrapItem>
  );
}

/** Stored artifact count and bytes per kind, and the total against the storage cap. */
export default function ArtifactChips({ artifacts }: ArtifactChipsProps) {
  const { locale, t } = useLocale();
  const kinds = Object.entries(artifacts.by_kind).sort(([a], [b]) =>
    a.localeCompare(b),
  );

  return (
    <>
      {kinds.map(([kind, totals]) => (
        <WrapItem key={kind}>
          <Badge variant="subtle" colorPalette="teal">
            {t("discovery_admin.artifacts.chip_kind", {
              kind: translateOrRaw(
                t,
                `discovery_admin.artifacts.kind_${kind}`,
                kind,
              ),
              count: totals.count,
              size: formatBytes(totals.bytes, locale),
            })}
          </Badge>
        </WrapItem>
      ))}
      <StorageChip artifacts={artifacts} />
    </>
  );
}

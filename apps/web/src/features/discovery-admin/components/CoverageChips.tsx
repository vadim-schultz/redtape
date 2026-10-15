import { Badge, HStack, Text, Wrap, WrapItem } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCoverageResponse } from "../types";

export interface CoverageChipsProps {
  coverage: DiscoveryCoverageResponse;
}

/** Summary chips for ingest coverage on the catalogue index. */
export default function CoverageChips({ coverage }: CoverageChipsProps) {
  const { t } = useLocale();
  const sourceEntries = Object.entries(coverage.by_source).sort(([a], [b]) =>
    a.localeCompare(b),
  );

  return (
    <Wrap gap={2}>
      {sourceEntries.map(([source, count]) => (
        <WrapItem key={source}>
          <Badge variant="subtle" colorPalette="blue">
            {t("discovery_admin.coverage.source_chip", { source, count })}
          </Badge>
        </WrapItem>
      ))}
      <WrapItem>
        <Badge variant="subtle" colorPalette="orange">
          {t("discovery_admin.coverage.tasks_pending", {
            count: coverage.tasks_pending,
          })}
        </Badge>
      </WrapItem>
      <WrapItem>
        <Badge variant="subtle" colorPalette="red">
          {t("discovery_admin.coverage.tasks_failed", {
            count: coverage.tasks_failed,
          })}
        </Badge>
      </WrapItem>
      <WrapItem>
        <Badge variant="subtle" colorPalette="green">
          {t("discovery_admin.coverage.emit_ready", {
            count: coverage.emit_ready_count,
          })}
        </Badge>
      </WrapItem>
      {sourceEntries.length === 0 ? (
        <HStack>
          <Text color="fg.muted" textStyle="bodySm">
            {t("discovery_admin.coverage.no_sources")}
          </Text>
        </HStack>
      ) : null}
    </Wrap>
  );
}

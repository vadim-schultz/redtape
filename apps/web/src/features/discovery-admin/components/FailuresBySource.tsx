import { Badge, HStack, Text, Wrap, WrapItem } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCoverageResponse } from "../types";

export interface FailuresBySourceProps {
  failures: DiscoveryCoverageResponse["failures_by_source"];
}

/** Failed task counts grouped by catalogue source, or an explicit empty note. */
export default function FailuresBySource({ failures }: FailuresBySourceProps) {
  const { t } = useLocale();
  const entries = Object.entries(failures).sort(([a], [b]) =>
    a.localeCompare(b),
  );

  return (
    <HStack align="start" gap={3} wrap="wrap">
      <Text textStyle="bodySm">
        {t("discovery_admin.coverage.failures_by_source")}
      </Text>
      {entries.length === 0 ? (
        <Text color="fg.muted" textStyle="bodySm">
          {t("discovery_admin.coverage.no_failures")}
        </Text>
      ) : (
        <Wrap gap={2}>
          {entries.map(([source, count]) => (
            <WrapItem key={source}>
              <Badge variant="subtle" colorPalette="red">
                {t("discovery_admin.coverage.source_chip", { source, count })}
              </Badge>
            </WrapItem>
          ))}
        </Wrap>
      )}
    </HStack>
  );
}

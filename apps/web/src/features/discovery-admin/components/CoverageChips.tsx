import { Badge, HStack, Stack, Text, Wrap, WrapItem } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCoverageResponse } from "../types";
import ArtifactChips from "./ArtifactChips";
import CandidateChips from "./CandidateChips";
import FailuresBySource from "./FailuresBySource";
import KindStatusChips from "./KindStatusChips";
import LastRunSummary from "./LastRunSummary";
import QueueStatusChips from "./QueueStatusChips";

export interface CoverageChipsProps {
  coverage: DiscoveryCoverageResponse;
}

/** Operational queue and ingest counts with the last successful worker run. */
export default function CoverageChips({ coverage }: CoverageChipsProps) {
  const { t } = useLocale();
  const sourceEntries = Object.entries(coverage.by_source).sort(([a], [b]) =>
    a.localeCompare(b),
  );

  return (
    <Stack gap={3}>
      <Wrap gap={2}>
        {sourceEntries.map(([source, count]) => (
          <WrapItem key={source}>
            <Badge variant="subtle" colorPalette="blue">
              {t("discovery_admin.coverage.source_chip", { source, count })}
            </Badge>
          </WrapItem>
        ))}
        <QueueStatusChips coverage={coverage} />
        <KindStatusChips coverage={coverage} />
        <CandidateChips candidates={coverage.candidates} />
        <ArtifactChips artifacts={coverage.artifacts} />
        {sourceEntries.length === 0 ? (
          <HStack>
            <Text color="fg.muted" textStyle="bodySm">
              {t("discovery_admin.coverage.no_sources")}
            </Text>
          </HStack>
        ) : null}
      </Wrap>
      <FailuresBySource failures={coverage.failures_by_source} />
      <LastRunSummary run={coverage.last_successful_run} />
    </Stack>
  );
}

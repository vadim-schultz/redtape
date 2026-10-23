import { Badge, WrapItem } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCoverageResponse } from "../types";

export interface QueueStatusChipsProps {
  coverage: DiscoveryCoverageResponse;
}

interface ChipSpec {
  key: string;
  palette: string;
  count: number;
}

function chipSpecs(coverage: DiscoveryCoverageResponse): ChipSpec[] {
  const { task_counts: counts } = coverage;
  return [
    { key: "tasks_total", palette: "gray", count: counts.total },
    { key: "tasks_pending", palette: "orange", count: counts.pending },
    { key: "tasks_claimed", palette: "blue", count: counts.claimed },
    { key: "tasks_completed", palette: "green", count: counts.completed },
    { key: "tasks_failed", palette: "red", count: counts.failed },
    {
      key: "fetch_attempts",
      palette: "gray",
      count: coverage.fetch_attempts_total,
    },
    { key: "stale_claims", palette: "red", count: coverage.stale_claims },
    { key: "stale_runs", palette: "red", count: coverage.stale_runs },
    { key: "emit_ready", palette: "green", count: coverage.emit_ready_count },
  ];
}

/** Queue status, fetch, lease, and emit-ready counts as chips. */
export default function QueueStatusChips({ coverage }: QueueStatusChipsProps) {
  const { t } = useLocale();

  return (
    <>
      {chipSpecs(coverage).map(({ key, palette, count }) => (
        <WrapItem key={key}>
          <Badge variant="subtle" colorPalette={palette}>
            {t(`discovery_admin.coverage.${key}`, { count })}
          </Badge>
        </WrapItem>
      ))}
    </>
  );
}

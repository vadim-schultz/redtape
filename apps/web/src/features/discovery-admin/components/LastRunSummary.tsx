import { Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryRun } from "../types";

export interface LastRunSummaryProps {
  run: DiscoveryRun | null;
}

/** Last successful worker run timestamp and report, or an explicit empty note. */
export default function LastRunSummary({ run }: LastRunSummaryProps) {
  const { t, locale } = useLocale();

  if (run === null) {
    return (
      <Text color="fg.muted" textStyle="bodySm">
        {t("discovery_admin.coverage.no_successful_run")}
      </Text>
    );
  }

  const finishedAt = run.finished_at
    ? new Date(run.finished_at).toLocaleString(locale)
    : "";

  return (
    <Stack gap={0}>
      <Text textStyle="bodySm">
        {t("discovery_admin.coverage.last_run", { finished_at: finishedAt })}
      </Text>
      <Text color="fg.muted" textStyle="bodySm">
        {t("discovery_admin.coverage.last_run_summary", {
          claimed: run.claimed_count,
          completed: run.completed_count,
          failed: run.failed_count,
          skipped: run.skipped_count,
          reason: run.stop_reason ?? "-",
        })}
      </Text>
    </Stack>
  );
}

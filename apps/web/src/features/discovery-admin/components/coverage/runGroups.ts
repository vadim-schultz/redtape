import { EMPTY_VALUE } from "../../../../utils/emptyValue";
import type { DiscoveryCoverageResponse, DiscoveryRun } from "../../types";
import {
  countRows,
  labelledRows,
  metricGroup,
  type MetricContext,
  type MetricGroup,
  type MetricRow,
} from "./metricModel";

/** Failed task counts per catalogue source. */
export function failureGroup(
  coverage: DiscoveryCoverageResponse,
  context: MetricContext,
): MetricGroup {
  return metricGroup(context, {
    key: "failures",
    titleKey: "failures_by_source",
    headerKeys: ["col_source", "tasks_failed"],
    emptyKey: "no_failures",
    rows: countRows(coverage.failures_by_source),
  });
}

function runRows(run: DiscoveryRun, context: MetricContext): MetricRow[] {
  const finished = run.finished_at
    ? new Date(run.finished_at).toLocaleString(context.locale)
    : EMPTY_VALUE;
  return labelledRows(context, [
    ["last_run_finished", finished],
    ["last_run_claimed", run.claimed_count],
    ["last_run_completed", run.completed_count],
    ["last_run_failed", run.failed_count],
    ["last_run_skipped", run.skipped_count],
    ["last_run_stop", run.stop_reason ?? EMPTY_VALUE],
  ]);
}

/** The last successful worker run as labelled rows, or an explicit empty note. */
export function lastRunGroup(
  coverage: DiscoveryCoverageResponse,
  context: MetricContext,
): MetricGroup {
  const run = coverage.last_successful_run;
  return metricGroup(context, {
    key: "last_run",
    titleKey: "group_last_run",
    headerKeys: ["col_metric", "col_value"],
    emptyKey: "no_successful_run",
    rows: run ? runRows(run, context) : [],
  });
}

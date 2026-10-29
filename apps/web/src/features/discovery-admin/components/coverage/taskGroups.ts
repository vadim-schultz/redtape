import type {
  DiscoveryCoverageResponse,
  DiscoveryTaskCounts,
} from "../../types";
import {
  attentionCell,
  coverageText,
  metricGroup,
  plain,
  sortedEntries,
  type MetricCell,
  type MetricContext,
  type MetricGroup,
  type MetricRow,
} from "./metricModel";

type QueueMetric = [key: string, count: number, flagged: boolean];

function queueMetrics(coverage: DiscoveryCoverageResponse): QueueMetric[] {
  const counts = coverage.task_counts;
  return [
    ["tasks_total", counts.total, false],
    ["tasks_pending", counts.pending, false],
    ["tasks_claimed", counts.claimed, false],
    ["tasks_completed", counts.completed, false],
    ["tasks_failed", counts.failed, true],
    ["fetch_attempts", coverage.fetch_attempts_total, false],
    ["stale_claims", coverage.stale_claims, true],
    ["stale_runs", coverage.stale_runs, true],
    ["emit_ready", coverage.emit_ready_count, false],
  ];
}

function queueRow(
  [key, count, flagged]: QueueMetric,
  context: MetricContext,
): MetricRow {
  return {
    key,
    label: coverageText(context, key),
    cells: [flagged ? attentionCell(count, context) : plain(count)],
  };
}

/** Queue status, fetch, lease and emit-ready counts; failures and stale work ask for attention. */
export function queueGroup(
  coverage: DiscoveryCoverageResponse,
  context: MetricContext,
): MetricGroup {
  return metricGroup(context, {
    key: "queue",
    titleKey: "group_queue",
    headerKeys: ["col_metric", "col_count"],
    rows: queueMetrics(coverage).map((metric) => queueRow(metric, context)),
  });
}

function kindCells(
  counts: DiscoveryTaskCounts,
  context: MetricContext,
): MetricCell[] {
  const { total, pending, claimed, completed, failed } = counts;
  return [
    plain(total),
    plain(pending),
    plain(claimed),
    plain(completed),
    attentionCell(failed, context),
  ];
}

/** One row per task kind, known or not, with the status split of its tasks. */
export function kindGroup(
  coverage: DiscoveryCoverageResponse,
  context: MetricContext,
): MetricGroup {
  const rows = sortedEntries(coverage.task_counts_by_kind).map(
    ([kind, counts]) => ({
      key: kind,
      label: kind,
      cells: kindCells(counts, context),
    }),
  );
  return metricGroup(context, {
    key: "kinds",
    titleKey: "group_kinds",
    headerKeys: [
      "col_kind",
      "col_total",
      "col_pending",
      "col_claimed",
      "col_done",
      "col_failed",
    ],
    emptyKey: "no_kinds",
    rows,
  });
}

import type {
  DiscoveryArtifactCoverage,
  DiscoveryCoverageResponse,
} from "../../types";
import { formatBytes } from "../../utils/formatBytes";
import { nearsStorageCap } from "../../utils/nearsStorageCap";
import { translateOrRaw } from "../../utils/translateOrRaw";
import {
  metricGroup,
  plain,
  sortedEntries,
  type MetricCell,
  type MetricContext,
  type MetricGroup,
  type MetricRow,
} from "./metricModel";

function kindRows(
  artifacts: DiscoveryArtifactCoverage,
  { locale, t }: MetricContext,
): MetricRow[] {
  return sortedEntries(artifacts.by_kind).map(([kind, totals]) => ({
    key: kind,
    label: translateOrRaw(t, `discovery_admin.artifacts.kind_${kind}`, kind),
    cells: [plain(totals.count), plain(formatBytes(totals.bytes, locale))],
  }));
}

function sizeCell(
  artifacts: DiscoveryArtifactCoverage,
  { locale, t }: MetricContext,
): MetricCell {
  const text = t("discovery_admin.artifacts.stored_of_cap", {
    size: formatBytes(artifacts.total_bytes, locale),
    cap: formatBytes(artifacts.bytes_cap, locale),
  });
  if (!nearsStorageCap(artifacts.total_bytes, artifacts.bytes_cap)) {
    return plain(text);
  }
  const label = t("discovery_admin.artifacts.stored_nearly_full");
  return { text, badge: { label, palette: "orange" } };
}

function totalRow(
  artifacts: DiscoveryArtifactCoverage,
  context: MetricContext,
): MetricRow {
  const kinds = Object.values(artifacts.by_kind);
  return {
    key: "total",
    label: context.t("discovery_admin.artifacts.stored_total"),
    cells: [
      plain(kinds.reduce((sum, { count }) => sum + count, 0)),
      sizeCell(artifacts, context),
    ],
  };
}

/** Stored artifacts per kind and the total against the storage cap. */
export function artifactGroup(
  coverage: DiscoveryCoverageResponse,
  context: MetricContext,
): MetricGroup {
  const { artifacts } = coverage;
  return metricGroup(context, {
    key: "artifacts",
    titleKey: "group_artifacts",
    headerKeys: ["col_artifact_kind", "col_files", "col_size"],
    rows: [...kindRows(artifacts, context), totalRow(artifacts, context)],
  });
}

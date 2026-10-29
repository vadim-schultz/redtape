import type { DiscoveryCoverageResponse } from "../../types";
import { artifactGroup } from "./artifactGroup";
import { candidateGroup, sourceGroup } from "./contentGroups";
import type { MetricContext, MetricGroup } from "./metricModel";
import { failureGroup, lastRunGroup } from "./runGroups";
import { kindGroup, queueGroup } from "./taskGroups";

type GroupBuilder = (
  coverage: DiscoveryCoverageResponse,
  context: MetricContext,
) => MetricGroup;

/** The static coverage groups in reading order: what exists, what is queued, what went wrong. */
const COVERAGE_GROUP_BUILDERS: GroupBuilder[] = [
  sourceGroup,
  queueGroup,
  kindGroup,
  candidateGroup,
  artifactGroup,
  failureGroup,
  lastRunGroup,
];

/** Row models of every coverage group, derived from one response without rendering. */
export function buildCoverageGroups(
  coverage: DiscoveryCoverageResponse,
  context: MetricContext,
): MetricGroup[] {
  return COVERAGE_GROUP_BUILDERS.map((build) => build(coverage, context));
}

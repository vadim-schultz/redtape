import type {
  DiscoveryCoverageResponse,
  DiscoveryLlmOutcomes,
} from "../../types";
import {
  countRows,
  labelledRows,
  metricGroup,
  type MetricContext,
  type MetricGroup,
} from "./metricModel";

const LLM_OUTCOMES: (keyof DiscoveryLlmOutcomes)[] = [
  "extracted",
  "no_documents",
  "login_wall",
  "no_content",
];

/** Catalogue row counts per source, known or not. */
export function sourceGroup(
  coverage: DiscoveryCoverageResponse,
  context: MetricContext,
): MetricGroup {
  return metricGroup(context, {
    key: "sources",
    titleKey: "group_sources",
    headerKeys: ["col_source", "col_count"],
    emptyKey: "no_sources",
    rows: countRows(coverage.by_source),
  });
}

/** Document candidates by lifecycle status, with the mention count. */
export function candidateGroup(
  coverage: DiscoveryCoverageResponse,
  context: MetricContext,
): MetricGroup {
  const { total, staged, emitted, mentions } = coverage.candidates;
  return metricGroup(context, {
    key: "candidates",
    titleKey: "group_candidates",
    headerKeys: ["col_metric", "col_count"],
    rows: labelledRows(context, [
      ["candidates_total", total],
      ["candidates_staged", staged],
      ["candidates_emitted", emitted],
      ["candidate_mentions", mentions],
    ]),
  });
}

/** What the model runs produced, one row per outcome. */
export function llmGroup(
  outcomes: DiscoveryLlmOutcomes,
  context: MetricContext,
): MetricGroup {
  return metricGroup(context, {
    key: "llm",
    titleKey: "llm.title",
    headerKeys: ["col_outcome", "col_count"],
    rows: labelledRows(
      context,
      LLM_OUTCOMES.map((outcome) => [`llm.${outcome}`, outcomes[outcome]]),
    ),
  });
}

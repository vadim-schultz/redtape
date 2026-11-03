import type { CompletenessFlags } from "../../candidates/types";

import type {
  DiscoveryArtifactKind,
  DiscoveryCandidateStatus,
  DiscoveryMentionRole,
  DiscoverySource,
  DiscoveryTaskKind,
  DiscoveryTaskStatus,
} from "./values";

export * from "./values";

/** Discovery task queue row from the admin API. */
export type DiscoveryTask = {
  id: string;
  catalogue_service_id: string;
  source: DiscoverySource;
  kind: DiscoveryTaskKind;
  target_url: string;
  status: DiscoveryTaskStatus;
  priority: number;
  attempt_count: number;
  not_before: string | null;
  input_key: string | null;
  /** Why a completed task produced nothing (`login_wall`, `oversize`, ...); open set. */
  result_note: string | null;
  lease_expires_at: string | null;
  created_at: string;
  updated_at: string;
};

/** Paginated discovery task queue from the admin API. */

export type DiscoveryTaskListResponse = {
  items: DiscoveryTask[];
  total: number;
  offset: number;
  limit: number;
};

export type CatalogueServiceSummary = {
  id: string;
  source: DiscoverySource;
  external_id: string;
  jurisdiction_id: string;
  title_i18n: Record<string, string>;
  pipeline_stage: string;
  portal_url: string | null;
  created_at: string;
  updated_at: string;
};

export type EmitPreviewItem = {
  claim_id: string;
  kind: string;
  payload: Record<string, unknown> | null;
  skip_reason: string | null;
};

export type EmitPreviewResponse = {
  items: EmitPreviewItem[];
};

export type CataloguePipelineResponse = {
  service: CatalogueServiceSummary;
  derived_stage: string;
  tasks: DiscoveryTask[];
  entities: Record<string, unknown>[];
  fetch_logs: Record<string, unknown>[];
  claims: Record<string, unknown>[];
  events: Record<string, unknown>[];
};

export type CatalogueSummaryChips = {
  total: number;
  by_source: Partial<Record<DiscoverySource, number>>;
  by_pipeline_stage: Record<string, number>;
};

export type CatalogueListResponse = {
  items: CatalogueServiceSummary[];
  summary: CatalogueSummaryChips;
  total: number;
  offset: number;
  limit: number;
};

export type DiscoveryTaskCounts = {
  total: number;
  pending: number;
  claimed: number;
  completed: number;
  failed: number;
};

export type DiscoveryCandidateCounts = {
  total: number;
  staged: number;
  emitted: number;
  mentions: number;
};

export type DiscoveryRun = {
  id: string;
  kind: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  claimed_count: number;
  completed_count: number;
  failed_count: number;
  skipped_count: number;
  remaining_count: number | null;
  stop_reason: string | null;
  error_detail: string | null;
};

/** Artifact count and stored bytes of one kind. */
export type DiscoveryArtifactTotals = { count: number; bytes: number };

/** Stored artifacts per kind against the storage cap the API reports. */
export type DiscoveryArtifactCoverage = {
  /** Keyed by artifact kind; a kind this client does not know yet still counts. */
  by_kind: Record<string, DiscoveryArtifactTotals>;
  total_bytes: number;
  bytes_cap: number;
};

/** Completed `llm_extract` tasks by what the model run produced. */
export type DiscoveryLlmOutcomes = {
  extracted: number;
  no_documents: number;
  login_wall: number;
  no_content: number;
};

export type DiscoveryCoverageResponse = {
  by_source: Partial<Record<DiscoverySource, number>>;
  tasks_pending: number;
  tasks_failed: number;
  emit_ready_count: number;
  task_counts: DiscoveryTaskCounts;
  /** Keyed by task kind; a kind this client does not know yet still renders. */
  task_counts_by_kind: Record<string, DiscoveryTaskCounts>;
  candidates: DiscoveryCandidateCounts;
  llm_outcomes: DiscoveryLlmOutcomes;
  artifacts: DiscoveryArtifactCoverage;
  fetch_attempts_total: number;
  stale_claims: number;
  stale_runs: number;
  failures_by_source: Partial<Record<DiscoverySource, number>>;
  last_successful_run: DiscoveryRun | null;
};

/** A document candidate as the detail route returns it. */
export type DiscoveryCandidateRecord = {
  id: string;
  jurisdiction_id: string;
  key: string;
  title_i18n: Record<string, string>;
  official_url: string | null;
  status: DiscoveryCandidateStatus;
  suggestion_id: string | null;
  mention_count: number;
  created_at: string;
  updated_at: string;
};

/** One listed document candidate with its mention statistics and completeness flags. */
export type DiscoveryCandidate = DiscoveryCandidateRecord & {
  roles: DiscoveryMentionRole[];
  jurisdiction_name_i18n: Record<string, string>;
  completeness: number;
  complete: boolean;
  flags: CompletenessFlags;
};

export type DiscoveryCandidateListResponse = {
  items: DiscoveryCandidate[];
  total: number;
  offset: number;
  limit: number;
};

/** One stored artifact; `url` is an opaque, short-lived link (null when storage is unset or denied). */
export type DiscoveryArtifact = {
  id: string;
  catalogue_service_id: string;
  discovery_task_id: string | null;
  kind: DiscoveryArtifactKind;
  content_type: string;
  byte_size: number;
  source_url: string;
  final_url: string | null;
  fetched_at: string;
  created_at: string;
  url: string | null;
};

export type DiscoveryArtifactListResponse = {
  items: DiscoveryArtifact[];
  total: number;
  offset: number;
  limit: number;
};

/** One free-tier resource in its current period. */
export type DiscoveryBudget = {
  resource: string;
  period: string;
  cap: number;
  used: number;
  remaining: number;
  exhausted: boolean;
};

export type DiscoveryBudgetsResponse = {
  items: DiscoveryBudget[];
  stored_bytes: number;
  stored_bytes_cap: number;
};

/** The artifact a mention cites, without its storage details. */
export type DiscoveryMentionArtifact = {
  id: string;
  kind: DiscoveryArtifactKind;
  fetched_at: string;
};

/** One occurrence of a candidate in a procedure. */
export type DiscoveryCandidateMention = {
  id: string;
  catalogue_service_id: string;
  procedure_title_i18n: Record<string, string>;
  procedure_source: DiscoverySource;
  portal_url: string | null;
  role: DiscoveryMentionRole;
  excerpt: string;
  source_field: string;
  artifact_id: string | null;
  artifact: DiscoveryMentionArtifact | null;
  extractor: string;
  extractor_version: string;
  /** When the document applies ("bei Zuzug aus dem Ausland"), as the page states it. */
  condition: string | null;
  is_optional: boolean | null;
  domain_codes: string[];
  situation_codes: string[];
  created_at: string;
};

/** How many procedures carry a tag code, and whether an emit would use it. */
export type DiscoveryTagSupport = {
  code: string;
  procedures: number;
  /** Share of the candidate's tagged procedures, from 0 to 1. */
  share: number;
  accepted: boolean;
};

export type DiscoveryCandidateDetailResponse = {
  candidate: DiscoveryCandidateRecord;
  jurisdiction_name_i18n: Record<string, string>;
  mentions: DiscoveryCandidateMention[];
  suggested_domain_codes: DiscoveryTagSupport[];
  suggested_situation_codes: DiscoveryTagSupport[];
};

/** A staged "parent requires required" edge with both titles and the stating procedure. */
export type DiscoveryCandidateEdge = {
  id: string;
  parent_candidate_id: string;
  parent_title_i18n: Record<string, string>;
  required_candidate_id: string;
  required_title_i18n: Record<string, string>;
  catalogue_service_id: string;
  procedure_title_i18n: Record<string, string>;
  /** Open set: `explicit`, `derived_single_issued`. */
  basis: string;
  condition: string | null;
  is_optional: boolean | null;
  excerpt: string;
  extractor: string;
  extractor_version: string;
  created_at: string;
};

/** Every edge that has the candidate as parent or as required end. */
export type DiscoveryCandidateEdgesResponse = {
  items: DiscoveryCandidateEdge[];
};

/** A catalogue entity or pending suggestion an emit would duplicate. */
export type DiscoveryEmitConflict = { type: string; id: string };

/** The `new_document` suggestion an emit would create. */
export type CandidateEmitSuggestion = {
  kind: string;
  jurisdiction_id: string;
  source_url: string;
  payload: {
    title_i18n?: Record<string, string>;
    official_url?: string | null;
  };
};

/** What emitting a candidate would do; nothing is written. */
export type CandidateEmitPreview = {
  candidate_id: string;
  suggestion: CandidateEmitSuggestion | null;
  suggestion_id: string | null;
  /** Open set: `duplicate`, `no_mentions`, `no_source_url`, `invalid_payload`, `already_emitted`. */
  skip_reason: string | null;
  conflicts: DiscoveryEmitConflict[];
};

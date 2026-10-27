/** Discovery task queue row from the admin API. */

export type DiscoveryTaskStatus =
  "pending" | "claimed" | "completed" | "failed";

export type DiscoverySource = "govdata" | "pvog" | "fim" | "leika" | "manual";

export type DiscoveryTaskKind =
  | "fetch_url"
  | "enrich_metadata"
  | "harvest_payload"
  | "extract_page"
  | "render_page"
  | "capture_screenshot";

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

export type DiscoveryArtifactKind = "html_snapshot" | "screenshot";

/** Artifact count and stored bytes of one kind. */
export type DiscoveryArtifactTotals = { count: number; bytes: number };

/** Stored artifacts per kind against the storage cap the API reports. */
export type DiscoveryArtifactCoverage = {
  /** Keyed by artifact kind; a kind this client does not know yet still counts. */
  by_kind: Record<string, DiscoveryArtifactTotals>;
  total_bytes: number;
  bytes_cap: number;
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
  artifacts: DiscoveryArtifactCoverage;
  fetch_attempts_total: number;
  stale_claims: number;
  stale_runs: number;
  failures_by_source: Partial<Record<DiscoverySource, number>>;
  last_successful_run: DiscoveryRun | null;
};

export type DiscoveryMentionRole = "required" | "form";

export type DiscoveryCandidateStatus = "staged" | "emitted";

export type DiscoveryCandidateSort = "mentions_desc" | "title_asc" | "newest";

/** One listed document candidate with its mention statistics. */
export type DiscoveryCandidate = {
  id: string;
  jurisdiction_id: string;
  key: string;
  title_i18n: Record<string, string>;
  official_url: string | null;
  status: DiscoveryCandidateStatus;
  suggestion_id: string | null;
  mention_count: number;
  roles: DiscoveryMentionRole[];
  jurisdiction_name_i18n: Record<string, string>;
  created_at: string;
  updated_at: string;
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

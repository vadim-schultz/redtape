/** Discovery task queue row from the admin API. */

export type DiscoveryTaskStatus =
  "pending" | "claimed" | "completed" | "failed";

export type DiscoverySource = "govdata" | "pvog" | "fim" | "leika" | "manual";

export type DiscoveryTaskKind = "fetch_url" | "enrich_metadata";

export type DiscoveryTask = {
  id: string;
  catalogue_service_id: string;
  source: DiscoverySource;
  kind: DiscoveryTaskKind;
  target_url: string;
  status: DiscoveryTaskStatus;
  priority: number;
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

export type DiscoveryCoverageResponse = {
  by_source: Partial<Record<DiscoverySource, number>>;
  tasks_pending: number;
  tasks_failed: number;
  emit_ready_count: number;
  task_counts: DiscoveryTaskCounts;
  fetch_attempts_total: number;
  stale_claims: number;
  stale_runs: number;
  failures_by_source: Partial<Record<DiscoverySource, number>>;
  last_successful_run: DiscoveryRun | null;
};

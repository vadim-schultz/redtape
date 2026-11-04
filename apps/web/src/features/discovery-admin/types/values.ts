// Each closed set is declared once, as a const array. The type is derived from
// the array, so a value added here reaches the unions, the filters and the
// sort controls at the same time. Mirrors the API enums and allowlists.

/** Sources the admin lists can be filtered by. */
export const DISCOVERY_SOURCES = [
  "govdata",
  "pvog",
  "fim",
  "leika",
  "manual",
] as const;
export type DiscoverySource = (typeof DISCOVERY_SOURCES)[number];

/** Task statuses in lifecycle order. */
export const TASK_STATUSES = [
  "pending",
  "claimed",
  "completed",
  "failed",
] as const;
export type DiscoveryTaskStatus = (typeof TASK_STATUSES)[number];

/** Task kinds in pipeline order. */
export const TASK_KINDS = [
  "fetch_url",
  "enrich_metadata",
  "harvest_payload",
  "extract_page",
  "render_page",
  "capture_screenshot",
  "llm_extract",
] as const;
export type DiscoveryTaskKind = (typeof TASK_KINDS)[number];

/** Candidate statuses in lifecycle order. */
export const CANDIDATE_STATUSES = ["staged", "emitted"] as const;
export type DiscoveryCandidateStatus = (typeof CANDIDATE_STATUSES)[number];

/** Roles a mention can play, in the order the documents list offers them. */
export const MENTION_ROLES = ["required", "form", "issued"] as const;
export type DiscoveryMentionRole = (typeof MENTION_ROLES)[number];

/** Stored artifact kinds. */
export const ARTIFACT_KINDS = ["html_snapshot", "screenshot"] as const;
export type DiscoveryArtifactKind = (typeof ARTIFACT_KINDS)[number];

/** Catalogue pipeline stages in order. */
export const PIPELINE_STAGES = ["T0", "T1", "T2", "T3", "T4"] as const;

/** Public sort keys of the task queue; the table maps its columns to these. */
export const TASK_SORT_KEYS = [
  "target",
  "kind",
  "status",
  "source",
  "priority",
  "attempts",
] as const;
export type TaskSortKey = (typeof TASK_SORT_KEYS)[number];

/** Filter keys the task queue accepts. */
export const TASK_FILTER_KEYS = ["status", "source", "kind"] as const;
export type TaskFilterKey = (typeof TASK_FILTER_KEYS)[number];

/** Public sort keys of the catalogue index. */
export const CATALOGUE_SORT_KEYS = [
  "external_id",
  "title",
  "source",
  "stage",
] as const;
export type CatalogueSortKey = (typeof CATALOGUE_SORT_KEYS)[number];

/** Filter keys the catalogue index accepts. */
export const CATALOGUE_FILTER_KEYS = ["source", "stage"] as const;
export type CatalogueFilterKey = (typeof CATALOGUE_FILTER_KEYS)[number];

/** Public sort keys of the candidate list. */
export const CANDIDATE_SORT_KEYS = [
  "mentions",
  "title",
  "created_at",
  "jurisdiction",
  "status",
  "roles",
  "completeness",
] as const;
export type CandidateSortKey = (typeof CANDIDATE_SORT_KEYS)[number];

/** Filter keys the candidate list accepts. */
export const CANDIDATE_FILTER_KEYS = [
  "status",
  "role",
  "source",
  "min_mentions",
  "complete",
] as const;
export type CandidateFilterKey = (typeof CANDIDATE_FILTER_KEYS)[number];

/** Values the `complete` candidate filter accepts. */
export const COMPLETE_CHOICES = ["yes", "no"] as const;

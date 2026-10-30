import type {
  DiscoveryCandidateStatus,
  DiscoveryMentionRole,
  DiscoverySource,
  DiscoveryTaskKind,
  DiscoveryTaskStatus,
} from "./index";

/** Sources the admin lists can be filtered by; mirrors the API enum. */
export const DISCOVERY_SOURCES = [
  "govdata",
  "pvog",
  "fim",
  "leika",
  "manual",
] as const satisfies readonly DiscoverySource[];

/** Task statuses in lifecycle order. */
export const TASK_STATUSES = [
  "pending",
  "claimed",
  "completed",
  "failed",
] as const satisfies readonly DiscoveryTaskStatus[];

/** Task kinds in pipeline order. */
export const TASK_KINDS = [
  "fetch_url",
  "enrich_metadata",
  "harvest_payload",
  "extract_page",
  "render_page",
  "capture_screenshot",
  "llm_extract",
] as const satisfies readonly DiscoveryTaskKind[];

/** Candidate statuses in lifecycle order. */
export const CANDIDATE_STATUSES = [
  "staged",
  "emitted",
] as const satisfies readonly DiscoveryCandidateStatus[];

/** Roles a mention can play, in the order the documents list offers them. */
export const MENTION_ROLES = [
  "required",
  "form",
  "issued",
] as const satisfies readonly DiscoveryMentionRole[];

import type {
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

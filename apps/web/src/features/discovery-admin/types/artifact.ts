import type { DiscoveryArtifactKind } from "./values";

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
  /** Where the bytes are stored; an internal key, not a link. */
  storage_key: string;
  sha256: string;
  url: string | null;
};

export type DiscoveryArtifactListResponse = {
  items: DiscoveryArtifact[];
  total: number;
  offset: number;
  limit: number;
};

/** The artifact a mention cites, without its storage details. */
export type DiscoveryMentionArtifact = {
  id: string;
  kind: DiscoveryArtifactKind;
  fetched_at: string;
};

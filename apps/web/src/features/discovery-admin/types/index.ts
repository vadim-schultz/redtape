/** Discovery task queue row from the admin API. */

export type DiscoveryTaskStatus =
  | "pending"
  | "claimed"
  | "completed"
  | "failed";

export type DiscoverySource =
  | "govdata"
  | "pvog"
  | "fim"
  | "leika"
  | "manual";

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

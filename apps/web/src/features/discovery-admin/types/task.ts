import type {
  DiscoverySource,
  DiscoveryTaskKind,
  DiscoveryTaskStatus,
} from "./values";

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

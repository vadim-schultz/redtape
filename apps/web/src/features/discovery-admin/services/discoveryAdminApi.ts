import { apiRequest } from "../../../services/api";
import type {
  DiscoverySource,
  DiscoveryTaskListResponse,
  DiscoveryTaskStatus,
} from "../types";

const TASKS_PATH = "/api/v1/discovery/admin/tasks";

/** Probe allowlist by listing tasks (server enforces admin emails). */
export async function probeDiscoveryAdminAccess(params: {
  locale: string;
  accessToken: string;
}): Promise<DiscoveryTaskListResponse> {
  const { locale, accessToken } = params;
  return apiRequest<DiscoveryTaskListResponse>(TASKS_PATH, {
    locale,
    accessToken,
    query: { limit: 1, offset: 0 },
  });
}

/** Paginated crawler queue with optional status and source filters. */
export async function listDiscoveryTasks(params: {
  locale: string;
  accessToken: string;
  status?: DiscoveryTaskStatus;
  source?: DiscoverySource;
  offset?: number;
  limit?: number;
}): Promise<DiscoveryTaskListResponse> {
  const {
    locale,
    accessToken,
    status,
    source,
    offset = 0,
    limit = 20,
  } = params;
  return apiRequest<DiscoveryTaskListResponse>(TASKS_PATH, {
    locale,
    accessToken,
    query: { status, source, offset, limit },
  });
}

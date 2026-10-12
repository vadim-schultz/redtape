import { apiRequest } from "../../../services/api";
import type { DiscoveryTaskListResponse } from "../types";

/** Probe allowlist by listing tasks (server enforces admin emails). */
export async function probeDiscoveryAdminAccess(params: {
  locale: string;
  accessToken: string;
}): Promise<DiscoveryTaskListResponse> {
  const { locale, accessToken } = params;
  return apiRequest<DiscoveryTaskListResponse>(
    "/api/v1/discovery/admin/tasks",
    {
      locale,
      accessToken,
      query: { limit: 1, offset: 0 },
    },
  );
}

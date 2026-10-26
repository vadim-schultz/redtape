import { apiRequest } from "../../../services/api";
import type {
  CatalogueListResponse,
  CataloguePipelineResponse,
  DiscoveryCandidateListResponse,
  DiscoveryCandidateSort,
  DiscoveryCoverageResponse,
  DiscoveryMentionRole,
  DiscoverySource,
  DiscoveryTaskKind,
  DiscoveryTaskListResponse,
  DiscoveryTaskStatus,
  EmitPreviewResponse,
} from "../types";

const TASKS_PATH = "/api/v1/discovery/admin/tasks";
const CATALOGUE_PATH = "/api/v1/discovery/admin/catalogue";
const CANDIDATES_PATH = "/api/v1/discovery/admin/candidates";
const COVERAGE_PATH = "/api/v1/discovery/admin/coverage";

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

/** Paginated crawler queue with optional status, source and kind filters. */
export async function listDiscoveryTasks(params: {
  locale: string;
  accessToken: string;
  status?: DiscoveryTaskStatus;
  source?: DiscoverySource;
  kind?: DiscoveryTaskKind;
  offset?: number;
  limit?: number;
}): Promise<DiscoveryTaskListResponse> {
  const {
    locale,
    accessToken,
    status,
    source,
    kind,
    offset = 0,
    limit = 20,
  } = params;
  return apiRequest<DiscoveryTaskListResponse>(TASKS_PATH, {
    locale,
    accessToken,
    query: { status, source, kind, offset, limit },
  });
}

/** Paginated imported catalogue rows for the admin index. */
export async function listDiscoveryCatalogue(params: {
  locale: string;
  accessToken: string;
  source?: DiscoverySource;
  offset?: number;
  limit?: number;
}): Promise<CatalogueListResponse> {
  const { locale, accessToken, source, offset = 0, limit = 20 } = params;
  return apiRequest<CatalogueListResponse>(CATALOGUE_PATH, {
    locale,
    accessToken,
    query: { source, offset, limit },
  });
}

/** Coverage metrics for catalogue index chips. */
export async function fetchDiscoveryCoverage(params: {
  locale: string;
  accessToken: string;
}): Promise<DiscoveryCoverageResponse> {
  const { locale, accessToken } = params;
  return apiRequest<DiscoveryCoverageResponse>(COVERAGE_PATH, {
    locale,
    accessToken,
  });
}

/** Full staging slice for one catalogue service. */
export async function fetchCataloguePipeline(params: {
  locale: string;
  accessToken: string;
  catalogueId: string;
}): Promise<CataloguePipelineResponse> {
  const { locale, accessToken, catalogueId } = params;
  return apiRequest<CataloguePipelineResponse>(
    `/api/v1/discovery/admin/catalogue/${catalogueId}/pipeline`,
    { locale, accessToken },
  );
}

/** Read-only preview of suggestion payloads for a catalogue service. */
export async function fetchEmitPreview(params: {
  locale: string;
  accessToken: string;
  catalogueId: string;
}): Promise<EmitPreviewResponse> {
  const { locale, accessToken, catalogueId } = params;
  return apiRequest<EmitPreviewResponse>(
    `/api/v1/discovery/admin/catalogue/${catalogueId}/emit-preview`,
    { locale, accessToken },
  );
}

/** Query of the document candidate list; unset filters are left out of the request. */
export type DiscoveryCandidateQuery = {
  q?: string;
  minMentions?: number;
  role?: DiscoveryMentionRole;
  source?: DiscoverySource;
  sort?: DiscoveryCandidateSort;
  offset?: number;
  limit?: number;
};

/** Paginated document candidates with search, filters and sort. */
export async function listDiscoveryCandidates(params: {
  locale: string;
  accessToken: string;
  query: DiscoveryCandidateQuery;
}): Promise<DiscoveryCandidateListResponse> {
  const { locale, accessToken, query } = params;
  const { minMentions, offset = 0, limit = 20, ...filters } = query;
  return apiRequest<DiscoveryCandidateListResponse>(CANDIDATES_PATH, {
    locale,
    accessToken,
    query: { ...filters, min_mentions: minMentions, offset, limit },
  });
}

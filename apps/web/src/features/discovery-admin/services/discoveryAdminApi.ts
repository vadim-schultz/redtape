import { apiRequest } from "../../../services/api";
import type {
  CandidateEmitPreview,
  CatalogueListResponse,
  CataloguePipelineResponse,
  DiscoveryArtifactListResponse,
  DiscoveryBudgetsResponse,
  DiscoveryCandidateDetailResponse,
  DiscoveryCandidateEdgesResponse,
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
const BUDGETS_PATH = "/api/v1/discovery/admin/budgets";
const ARTIFACT_PAGE_SIZE = 50;

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

/** One candidate with its jurisdiction name, mentions and their artifact summaries. */
export async function fetchDiscoveryCandidate(params: {
  locale: string;
  accessToken: string;
  candidateId: string;
}): Promise<DiscoveryCandidateDetailResponse> {
  const { locale, accessToken, candidateId } = params;
  return apiRequest<DiscoveryCandidateDetailResponse>(
    `${CANDIDATES_PATH}/${candidateId}`,
    { locale, accessToken },
  );
}

/** Every staged edge that has the candidate as parent or as required end. */
export async function fetchCandidateEdges(params: {
  locale: string;
  accessToken: string;
  candidateId: string;
}): Promise<DiscoveryCandidateEdgesResponse> {
  const { locale, accessToken, candidateId } = params;
  return apiRequest<DiscoveryCandidateEdgesResponse>(
    `${CANDIDATES_PATH}/${candidateId}/edges`,
    { locale, accessToken },
  );
}

/** Read-only preview of the suggestion emitting one candidate would create. */
export async function fetchCandidateEmitPreview(params: {
  locale: string;
  accessToken: string;
  candidateId: string;
}): Promise<CandidateEmitPreview> {
  const { locale, accessToken, candidateId } = params;
  return apiRequest<CandidateEmitPreview>(
    `${CANDIDATES_PATH}/${candidateId}/emit-preview`,
    { locale, accessToken },
  );
}

/** Artifacts of one catalogue row, each with a short-lived presigned URL. */
export async function listCatalogueArtifacts(params: {
  locale: string;
  accessToken: string;
  catalogueId: string;
}): Promise<DiscoveryArtifactListResponse> {
  const { locale, accessToken, catalogueId } = params;
  return apiRequest<DiscoveryArtifactListResponse>(
    `${CATALOGUE_PATH}/${catalogueId}/artifacts`,
    { locale, accessToken, query: { offset: 0, limit: ARTIFACT_PAGE_SIZE } },
  );
}

/** The evidence behind one candidate (cited artifacts and procedure screenshots), each with a presigned URL. */
export async function listCandidateArtifacts(params: {
  locale: string;
  accessToken: string;
  candidateId: string;
}): Promise<DiscoveryArtifactListResponse> {
  const { locale, accessToken, candidateId } = params;
  return apiRequest<DiscoveryArtifactListResponse>(
    `${CANDIDATES_PATH}/${candidateId}/artifacts`,
    { locale, accessToken, query: { offset: 0, limit: ARTIFACT_PAGE_SIZE } },
  );
}

/** Free-tier budgets of the current periods plus the stored-bytes figure. */
export async function fetchDiscoveryBudgets(params: {
  locale: string;
  accessToken: string;
}): Promise<DiscoveryBudgetsResponse> {
  const { locale, accessToken } = params;
  return apiRequest<DiscoveryBudgetsResponse>(BUDGETS_PATH, {
    locale,
    accessToken,
  });
}

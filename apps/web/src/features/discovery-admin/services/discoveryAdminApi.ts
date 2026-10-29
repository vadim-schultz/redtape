import { apiRequest } from "../../../services/api";
import { toListParams } from "../../../services/listQuery";
import type {
  CandidateEmitPreview,
  CatalogueListResponse,
  CataloguePipelineResponse,
  DiscoveryArtifactListResponse,
  DiscoveryBudgetsResponse,
  DiscoveryCandidateDetailResponse,
  DiscoveryCandidateEdgesResponse,
  DiscoveryCandidateListResponse,
  DiscoveryCoverageResponse,
  DiscoveryTaskListResponse,
  EmitPreviewResponse,
} from "../types";
import type { CandidateListQuery } from "./candidateListQuery";
import type { CatalogueListQuery } from "./catalogueListQuery";
import type { TaskListQuery } from "./taskListQuery";

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

/** Paginated crawler queue; the typed query is sent in its canonical parameter shape. */
export async function listDiscoveryTasks(params: {
  locale: string;
  accessToken: string;
  query: TaskListQuery;
}): Promise<DiscoveryTaskListResponse> {
  const { locale, accessToken, query } = params;
  return apiRequest<DiscoveryTaskListResponse>(TASKS_PATH, {
    locale,
    accessToken,
    query: toListParams(query),
  });
}

/** Paginated imported catalogue rows; the typed query is sent in its canonical parameter shape. */
export async function listDiscoveryCatalogue(params: {
  locale: string;
  accessToken: string;
  query: CatalogueListQuery;
}): Promise<CatalogueListResponse> {
  const { locale, accessToken, query } = params;
  return apiRequest<CatalogueListResponse>(CATALOGUE_PATH, {
    locale,
    accessToken,
    query: toListParams(query),
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

/** Paginated document candidates; the typed query is sent in its canonical parameter shape. */
export async function listDiscoveryCandidates(params: {
  locale: string;
  accessToken: string;
  query: CandidateListQuery;
}): Promise<DiscoveryCandidateListResponse> {
  const { locale, accessToken, query } = params;
  return apiRequest<DiscoveryCandidateListResponse>(CANDIDATES_PATH, {
    locale,
    accessToken,
    query: toListParams(query),
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

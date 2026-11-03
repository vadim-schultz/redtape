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
const ARTIFACT_LIST_PARAMS = { offset: 0, limit: 50 };

/** Locale and bearer token every discovery-admin service call needs. */
export type AdminAuth = { locale: string; accessToken: string };

/** Probe allowlist by listing tasks (server enforces admin emails). */
export async function probeDiscoveryAdminAccess(
  auth: AdminAuth,
): Promise<DiscoveryTaskListResponse> {
  return apiRequest<DiscoveryTaskListResponse>(TASKS_PATH, {
    ...auth,
    query: { limit: 1, offset: 0 },
  });
}

/** Paginated crawler queue; the typed query is sent in its canonical parameter shape. */
export async function listDiscoveryTasks(
  auth: AdminAuth,
  query: TaskListQuery,
): Promise<DiscoveryTaskListResponse> {
  return apiRequest<DiscoveryTaskListResponse>(TASKS_PATH, {
    ...auth,
    query: toListParams(query),
  });
}

/** Paginated imported catalogue rows; the typed query is sent in its canonical parameter shape. */
export async function listDiscoveryCatalogue(
  auth: AdminAuth,
  query: CatalogueListQuery,
): Promise<CatalogueListResponse> {
  return apiRequest<CatalogueListResponse>(CATALOGUE_PATH, {
    ...auth,
    query: toListParams(query),
  });
}

/** Coverage metrics for catalogue index chips. */
export async function fetchDiscoveryCoverage(
  auth: AdminAuth,
): Promise<DiscoveryCoverageResponse> {
  return apiRequest<DiscoveryCoverageResponse>(COVERAGE_PATH, auth);
}

/** Full staging slice for one catalogue service. */
export async function fetchCataloguePipeline(
  auth: AdminAuth,
  catalogueId: string,
): Promise<CataloguePipelineResponse> {
  return apiRequest<CataloguePipelineResponse>(
    `${CATALOGUE_PATH}/${catalogueId}/pipeline`,
    auth,
  );
}

/** Read-only preview of suggestion payloads for a catalogue service. */
export async function fetchEmitPreview(
  auth: AdminAuth,
  catalogueId: string,
): Promise<EmitPreviewResponse> {
  return apiRequest<EmitPreviewResponse>(
    `${CATALOGUE_PATH}/${catalogueId}/emit-preview`,
    auth,
  );
}

/** Paginated document candidates; the typed query is sent in its canonical parameter shape. */
export async function listDiscoveryCandidates(
  auth: AdminAuth,
  query: CandidateListQuery,
): Promise<DiscoveryCandidateListResponse> {
  return apiRequest<DiscoveryCandidateListResponse>(CANDIDATES_PATH, {
    ...auth,
    query: toListParams(query),
  });
}

/** One candidate with its jurisdiction name, mentions and their artifact summaries. */
export async function fetchDiscoveryCandidate(
  auth: AdminAuth,
  candidateId: string,
): Promise<DiscoveryCandidateDetailResponse> {
  return apiRequest<DiscoveryCandidateDetailResponse>(
    `${CANDIDATES_PATH}/${candidateId}`,
    auth,
  );
}

/** Every staged edge that has the candidate as parent or as required end. */
export async function fetchCandidateEdges(
  auth: AdminAuth,
  candidateId: string,
): Promise<DiscoveryCandidateEdgesResponse> {
  return apiRequest<DiscoveryCandidateEdgesResponse>(
    `${CANDIDATES_PATH}/${candidateId}/edges`,
    auth,
  );
}

/** Read-only preview of the suggestion emitting one candidate would create. */
export async function fetchCandidateEmitPreview(
  auth: AdminAuth,
  candidateId: string,
): Promise<CandidateEmitPreview> {
  return apiRequest<CandidateEmitPreview>(
    `${CANDIDATES_PATH}/${candidateId}/emit-preview`,
    auth,
  );
}

/** Artifacts of one catalogue row, each with a short-lived presigned URL. */
export async function listCatalogueArtifacts(
  auth: AdminAuth,
  catalogueId: string,
): Promise<DiscoveryArtifactListResponse> {
  return apiRequest<DiscoveryArtifactListResponse>(
    `${CATALOGUE_PATH}/${catalogueId}/artifacts`,
    { ...auth, query: ARTIFACT_LIST_PARAMS },
  );
}

/** The evidence behind one candidate (cited artifacts and procedure screenshots), each with a presigned URL. */
export async function listCandidateArtifacts(
  auth: AdminAuth,
  candidateId: string,
): Promise<DiscoveryArtifactListResponse> {
  return apiRequest<DiscoveryArtifactListResponse>(
    `${CANDIDATES_PATH}/${candidateId}/artifacts`,
    { ...auth, query: ARTIFACT_LIST_PARAMS },
  );
}

/** Free-tier budgets of the current periods plus the stored-bytes figure. */
export async function fetchDiscoveryBudgets(
  auth: AdminAuth,
): Promise<DiscoveryBudgetsResponse> {
  return apiRequest<DiscoveryBudgetsResponse>(BUDGETS_PATH, auth);
}

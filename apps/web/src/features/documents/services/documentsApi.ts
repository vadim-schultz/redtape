import { apiRequest } from "../../../services/api";
import { toListParams } from "../../../services/listQuery";
import type { CandidateListResponse } from "../../candidates/types";
import type {
  DocumentDetail,
  DocumentListRequest,
  DocumentListResponse,
} from "../types";
import { toDocumentListResponse } from "./documentMapper";

/** Selected codes as the API's CSV filter, or nothing when none. */
function codesFilter(codes: string[]): string | undefined {
  return codes.length > 0 ? codes.join(",") : undefined;
}

/** One page of documents filtered by canonical categories. */
export async function fetchDocuments(params: {
  locale: string;
  request: DocumentListRequest;
}): Promise<DocumentListResponse> {
  const { locale, request } = params;
  const { categories, query } = request;
  const page = await apiRequest<CandidateListResponse>("/api/v1/candidates", {
    method: "GET",
    locale,
    query: toListParams({
      ...query,
      filters: {
        category: codesFilter(categories),
      },
    }),
  });
  return toDocumentListResponse(page);
}

export async function fetchDocumentDetail(params: {
  locale: string;
  id: string;
}): Promise<DocumentDetail> {
  const { locale, id } = params;

  return apiRequest<DocumentDetail>(`/api/v1/documents/${id}`, {
    locale,
    method: "GET",
  });
}

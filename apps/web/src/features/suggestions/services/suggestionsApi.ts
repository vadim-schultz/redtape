import { apiRequest, ApiRequestError } from "../../../services/api";
import type {
  Conflict,
  CreateSuggestionRequest,
  SuggestionListResponse,
  SuggestionRead,
} from "../types";

export class SuggestionConflictError extends Error {
  conflicts: Conflict[];

  constructor(conflicts: Conflict[]) {
    super("Duplicate suggestion");
    this.name = "SuggestionConflictError";
    this.conflicts = conflicts;
  }
}

function conflictsFrom(bodyText: string): Conflict[] {
  try {
    const body = JSON.parse(bodyText) as { extra?: { conflicts?: Conflict[] } };
    return body.extra?.conflicts ?? [];
  } catch {
    return [];
  }
}

export async function createSuggestion(params: {
  locale: string;
  accessToken: string;
  request: CreateSuggestionRequest;
}): Promise<SuggestionRead> {
  const { locale, accessToken, request } = params;

  try {
    return await apiRequest<SuggestionRead>("/api/v1/suggestions", {
      method: "POST",
      locale,
      accessToken,
      body: request,
    });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 409) {
      throw new SuggestionConflictError(conflictsFrom(error.bodyText));
    }
    throw error;
  }
}

export async function fetchSuggestions(params: {
  locale: string;
  status?: string[];
  kind?: string;
  jurisdictionId?: string;
}): Promise<SuggestionListResponse> {
  const { locale, status, kind, jurisdictionId } = params;

  return apiRequest<SuggestionListResponse>("/api/v1/suggestions", {
    method: "GET",
    locale,
    query: {
      status,
      kind,
      jurisdiction_id: jurisdictionId,
    },
  });
}

export async function fetchSuggestionDetail(params: {
  locale: string;
  id: string;
}): Promise<SuggestionRead> {
  const { locale, id } = params;

  return apiRequest<SuggestionRead>(`/api/v1/suggestions/${id}`, {
    locale,
    method: "GET",
  });
}

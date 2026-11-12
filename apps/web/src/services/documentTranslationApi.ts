import {
  DOCUMENT_TRANSLATION_CODES,
  type DocumentTranslationCode,
  type DocumentTranslationError,
  type DocumentTranslationRead,
} from "../types/documentTranslation";
import { ApiRequestError, apiRequest } from "./api";

/** What the route answered: the page's blocks, or the 404 that says why there are none. */
export type DocumentTranslationAnswer =
  | { state: "ready"; document: DocumentTranslationRead }
  | { state: "unavailable"; body: DocumentTranslationError };

type RawBody = { code?: unknown; reason?: unknown };

function isCode(value: unknown): value is DocumentTranslationCode {
  return DOCUMENT_TRANSLATION_CODES.some((code) => code === value);
}

function parseBody(text: string): RawBody | null {
  try {
    const value: unknown = JSON.parse(text);
    return typeof value === "object" && value !== null
      ? (value as RawBody)
      : null;
  } catch {
    return null;
  }
}

/** The 404 body when it names a known code; null for every other failure. */
function unavailableBody(error: unknown): DocumentTranslationError | null {
  if (!(error instanceof ApiRequestError) || error.status !== 404) return null;
  const body = parseBody(error.bodyText);
  if (body === null || !isCode(body.code)) return null;
  return {
    code: body.code,
    reason: typeof body.reason === "string" ? body.reason : null,
  };
}

/** The translated blocks of a candidate's page in `locale`. A 404 with a known code is an answer, not a failure. */
export async function fetchDocumentTranslation(params: {
  id: string;
  locale: string;
}): Promise<DocumentTranslationAnswer> {
  const { id, locale } = params;
  try {
    const document = await apiRequest<DocumentTranslationRead>(
      `/api/v1/candidates/${encodeURIComponent(id)}/document-translation`,
      { locale, query: { locale } },
    );
    return { state: "ready", document };
  } catch (error) {
    const body = unavailableBody(error);
    if (body === null) throw error;
    return { state: "unavailable", body };
  }
}

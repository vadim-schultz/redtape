import type { DocumentTranslationAnswer } from "../../../../services/documentTranslationApi";
import type {
  DocumentTranslationCode,
  DocumentTranslationRead,
} from "../../../../types/documentTranslation";

/** The notes the section can show; each has one translation key. */
export type DocumentNote =
  | "pending"
  | "no_document"
  | "candidate_not_found"
  | "skipped"
  | "skipped_too_short"
  | "skipped_not_german"
  | "stale"
  | "truncated";

/** What the section renders: loading, the retryable error, a note for a page without blocks, or the page. */
export type DocumentView =
  | { state: "loading" }
  | { state: "error" }
  | { state: "unavailable"; note: DocumentNote }
  | { state: "ready"; document: DocumentTranslationRead };

const CODE_NOTES: Record<
  Exclude<DocumentTranslationCode, "skipped">,
  DocumentNote
> = {
  translation_pending: "pending",
  no_document: "no_document",
  candidate_not_found: "candidate_not_found",
};

const SKIP_NOTES = new Map<string, DocumentNote>([
  ["too_short", "skipped_too_short"],
  ["not_german", "skipped_not_german"],
]);

/** The note for a 404 code; a skip maps its reason, and an unknown reason falls back to the generic skip note. */
export function noteFor(
  code: DocumentTranslationCode,
  reason: string | null,
): DocumentNote {
  if (code !== "skipped") return CODE_NOTES[code];
  return SKIP_NOTES.get(reason ?? "") ?? "skipped";
}

/** The view of the query. Ready content stays on screen when a later refetch fails. */
export function toDocumentView(query: {
  data: DocumentTranslationAnswer | undefined;
  isError: boolean;
}): DocumentView {
  const { data } = query;
  if (data === undefined)
    return query.isError ? { state: "error" } : { state: "loading" };
  if (data.state === "unavailable")
    return {
      state: "unavailable",
      note: noteFor(data.body.code, data.body.reason),
    };
  return { state: "ready", document: data.document };
}

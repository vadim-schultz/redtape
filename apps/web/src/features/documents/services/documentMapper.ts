import type {
  CandidateCard,
  CandidateListResponse,
  SearchMode,
} from "../../candidates/types";
import type {
  DocumentListResponse,
  DocumentSummary,
  DocumentTag,
} from "../types";

/** Canonical category tags in the API's confidence order. */
function categoryTags(card: CandidateCard): DocumentTag[] {
  return [...card.categories].sort((a, b) => b.confidence - a.confidence);
}

/** The similarity a card shows: only hybrid matches have one, whatever else the payload carries. */
function similarityIn(card: CandidateCard, mode: SearchMode): number | null {
  return mode === "hybrid" ? (card.similarity ?? null) : null;
}

/** A candidate card as the documents list shows it. */
export function toDocumentSummary(
  card: CandidateCard,
  mode: SearchMode = "browse",
): DocumentSummary {
  return {
    id: card.id,
    title: card.title,
    description: card.description,
    tags: categoryTags(card),
    confidence: card.confidence,
    similarity: similarityIn(card, mode),
    translation: card.translation ?? null,
  };
}

/** A page of candidates as a page of documents. */
export function toDocumentListResponse(
  page: CandidateListResponse,
): DocumentListResponse {
  const mode = page.search_mode ?? "browse";

  return {
    ...page,
    search_mode: mode,
    items: page.items.map((card) => toDocumentSummary(card, mode)),
  };
}

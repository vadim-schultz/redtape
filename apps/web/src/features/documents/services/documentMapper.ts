import type {
  CandidateCard,
  CandidateListResponse,
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

/** A candidate card as the documents list shows it. */
export function toDocumentSummary(card: CandidateCard): DocumentSummary {
  return {
    id: card.id,
    title: card.title,
    description: card.description,
    tags: categoryTags(card),
    confidence: card.confidence,
  };
}

/** A page of candidates as a page of documents. */
export function toDocumentListResponse(
  page: CandidateListResponse,
): DocumentListResponse {
  return { ...page, items: page.items.map(toDocumentSummary) };
}

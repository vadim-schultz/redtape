import type {
  CandidateCard,
  CandidateListResponse,
  TaxonomyTag,
} from "../../candidates/types";
import type {
  DocumentAxis,
  DocumentListResponse,
  DocumentSummary,
  DocumentTag,
} from "../types";

function toTags(axis: DocumentAxis, tags: TaxonomyTag[]): DocumentTag[] {
  return tags.map(({ code, name, confidence }) => ({
    axis,
    code,
    name,
    confidence,
  }));
}

/** Both axes' tags in one list, most confident first. */
function mergedTags(card: CandidateCard): DocumentTag[] {
  return [
    ...toTags("domain", card.domains),
    ...toTags("situation", card.situations),
  ].sort((a, b) => b.confidence - a.confidence);
}

/** A candidate card as the documents list shows it. */
export function toDocumentSummary(card: CandidateCard): DocumentSummary {
  return {
    id: card.id,
    title: card.title,
    description: card.description,
    tags: mergedTags(card),
    confidence: card.confidence,
  };
}

/** A page of candidates as a page of documents. */
export function toDocumentListResponse(
  page: CandidateListResponse,
): DocumentListResponse {
  return { ...page, items: page.items.map(toDocumentSummary) };
}

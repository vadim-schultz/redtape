import type { ListQueryState } from "../../../services/listQuery";
import type { CategoryTag } from "../../taxonomy/types";

export type DocumentTag = CategoryTag;

/** One listed document (a discovered candidate); `tags` run most confident first. */
export type DocumentSummary = {
  id: string;
  title: string;
  description: string | null;
  tags: DocumentTag[];
  confidence: number;
};

export type DocumentListResponse = {
  items: DocumentSummary[];
  total: number;
  offset: number;
  limit: number;
};

/** Sort keys of the documents list, in the order the sort control offers them. */
export const DOCUMENT_SORT_KEYS = [
  "confidence",
  "title",
  "created_at",
] as const;
export type DocumentSortKey = (typeof DOCUMENT_SORT_KEYS)[number];

/** Search, sort and page of the documents list; the taxonomy chips travel beside it. */
export type DocumentListQuery = ListQueryState<DocumentSortKey, never>;

/** Everything one page of the documents list depends on. */
export type DocumentListRequest = {
  categories: string[];
  query: DocumentListQuery;
};

/** A document as the dormant requirement list names it. */
export type RequiredDocument = {
  id: string;
  slug: string;
  title: string;
  description?: string | null;
};

export type JurisdictionPathNode = {
  code: string;
  name: string;
  kind: string;
  openplz_type?: string | null;
};

export type RequirementRead = {
  id: string;
  required_document: RequiredDocument;
  notes: string | null;
};

export type DocumentDetail = {
  id: string;
  slug: string;
  title: string;
  description?: string | null;
  official_url: string | null;
  jurisdiction_id: string;
  jurisdiction_path: JurisdictionPathNode[];
  requirements: RequirementRead[];
  categories?: CategoryTag[];
};

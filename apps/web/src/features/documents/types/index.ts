import type { ListQueryState } from "../../../services/listQuery";
import type { TaggedTerm } from "../../taxonomy/types";

export type DocumentAxis = "domain" | "situation";

/** One tag of a listed document: its axis, localized name and score in `[0, 1]`. */
export type DocumentTag = Pick<TaggedTerm, "code" | "name" | "confidence"> & {
  axis: DocumentAxis;
};

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
  domains: string[];
  situations: string[];
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
  domains?: TaggedTerm[];
  life_situations?: TaggedTerm[];
};

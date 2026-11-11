import type { ListQueryState } from "../../../services/listQuery";
import type { SearchMode } from "../../candidates/types";
import type { CategoryTag } from "../../taxonomy/types";

export type DocumentTag = CategoryTag;

/** One listed document (a discovered candidate); `tags` run most confident first. */
export type DocumentSummary = {
  id: string;
  title: string;
  description: string | null;
  tags: DocumentTag[];
  confidence: number;
  /** Query match in 0..1; null when the list is not a hybrid search, so no ring shows. */
  similarity: number | null;
};

export type DocumentListResponse = {
  items: DocumentSummary[];
  total: number;
  offset: number;
  limit: number;
  search_mode: SearchMode;
};

/** Search and page of the documents list (results are always best first, so there is no sort); the taxonomy chips travel beside it. */
export type DocumentListQuery = ListQueryState<never, never>;

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

/** A localized root or subcategory returned by the canonical taxonomy endpoint. */
export type CategoryNode = {
  code: string;
  name: string;
  description: string;
  icon: string | null;
  parent_code: string | null;
  children: CategoryNode[];
};

/** A canonical category attached to a document, carrying its persisted confidence. */
export type CategoryTag = {
  code: string;
  name: string;
  confidence: number;
};

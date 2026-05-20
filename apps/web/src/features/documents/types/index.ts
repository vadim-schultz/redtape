export type DocumentSummary = {
  id: string;
  slug: string;
  title: string;
  description?: string | null;
};

export type DocumentListResponse = {
  items: DocumentSummary[];
  total: number;
  offset: number;
  limit: number;
};

export type JurisdictionPathNode = {
  code: string;
  name: string;
  kind: string;
  openplz_type?: string | null;
};

export type RequirementRead = {
  id: string;
  required_document: DocumentSummary;
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
};


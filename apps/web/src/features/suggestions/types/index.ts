export type SuggestionPayload = {
  title_i18n: Record<string, string>;
  description_i18n?: Record<string, string>;
  official_url: string;
  domain_codes: string[];
  situation_codes: string[];
};

export type CreateSuggestionRequest = {
  municipality_code: string;
  payload: SuggestionPayload;
};

export type Conflict = {
  type: "document" | "suggestion" | "document_requirement";
  id: string;
};

export type SubmitterRead = {
  kind: "user" | "crawler";
  display_name: string | null;
};

export type SuggestionRead = {
  id: string;
  kind: string;
  status: string;
  source_type: string;
  jurisdiction_id: string;
  payload: SuggestionPayload;
  source_url: string | null;
  submitted_by: SubmitterRead;
  created_at: string;
};

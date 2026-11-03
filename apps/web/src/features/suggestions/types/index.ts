import type {
  SuggestionKind,
  SuggestionSourceType,
  SuggestionStatus,
} from "./values";

export * from "./values";

export type SuggestionPayload = {
  title_i18n: Record<string, string>;
  description_i18n?: Record<string, string>;
  official_url?: string | null;
  domain_codes: string[];
  situation_codes: string[];
};

export type NewRequirementSuggestionPayload = {
  parent_document_id: string;
  required_document_id: string;
  notes_i18n?: Record<string, string> | null;
};

export type SubmitterRead = {
  kind: "user" | "crawler";
  display_name: string | null;
};

export type SuggestionRead = {
  id: string;
  kind: SuggestionKind;
  status: SuggestionStatus;
  source_type: SuggestionSourceType;
  jurisdiction_id: string;
  payload: SuggestionPayload | NewRequirementSuggestionPayload;
  source_url: string | null;
  submitted_by: SubmitterRead;
  created_at: string;
};

export type SuggestionListResponse = {
  items: SuggestionRead[];
  total: number;
  offset: number;
  limit: number;
};

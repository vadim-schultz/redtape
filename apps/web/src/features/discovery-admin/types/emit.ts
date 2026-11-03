export type EmitPreviewItem = {
  claim_id: string;
  kind: string;
  payload: Record<string, unknown> | null;
  skip_reason: string | null;
};

export type EmitPreviewResponse = {
  items: EmitPreviewItem[];
};

/** A catalogue entity or pending suggestion an emit would duplicate. */
export type DiscoveryEmitConflict = { type: string; id: string };

/** The `new_document` suggestion an emit would create. */
export type CandidateEmitSuggestion = {
  kind: string;
  jurisdiction_id: string;
  source_url: string;
  payload: {
    title_i18n?: Record<string, string>;
    official_url?: string | null;
  };
};

/** What emitting a candidate would do; nothing is written. */
export type CandidateEmitPreview = {
  candidate_id: string;
  suggestion: CandidateEmitSuggestion | null;
  suggestion_id: string | null;
  /** Open set: `duplicate`, `no_mentions`, `no_source_url`, `invalid_payload`, `already_emitted`. */
  skip_reason: string | null;
  conflicts: DiscoveryEmitConflict[];
};

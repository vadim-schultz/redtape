export type EvidenceKind = "screenshot" | "html";

export type EvidenceRead = {
  id: string;
  kind: EvidenceKind;
  source_url: string;
  fetched_at: string;
  url: string;
  content_type: string;
  byte_size: number;
};

export type EvidenceListResponse = {
  items: EvidenceRead[];
};

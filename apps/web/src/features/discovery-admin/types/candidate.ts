import type { CompletenessFlags } from "../../candidates/types";

import type { DiscoveryMentionArtifact } from "./artifact";
import type {
  DiscoveryCandidateStatus,
  DiscoveryMentionRole,
  DiscoverySource,
} from "./values";

/** A document candidate as the detail route returns it. */
export type DiscoveryCandidateRecord = {
  id: string;
  jurisdiction_id: string;
  key: string;
  title_i18n: Record<string, string>;
  official_url: string | null;
  status: DiscoveryCandidateStatus;
  suggestion_id: string | null;
  mention_count: number;
  created_at: string;
  updated_at: string;
};

/** One listed document candidate with its mention statistics and completeness flags. */
export type DiscoveryCandidate = DiscoveryCandidateRecord & {
  roles: DiscoveryMentionRole[];
  jurisdiction_name_i18n: Record<string, string>;
  completeness: number;
  complete: boolean;
  flags: CompletenessFlags;
};

export type DiscoveryCandidateListResponse = {
  items: DiscoveryCandidate[];
  total: number;
  offset: number;
  limit: number;
};

export type PvogSourcePath = {
  root_code: string | null;
  root_label: string | null;
  parent_code: string | null;
  parent_label: string | null;
  leaf_code: string | null;
  leaf_label: string | null;
  source_version: string | null;
};

/** One occurrence of a candidate in a procedure. */
export type DiscoveryCandidateMention = {
  id: string;
  catalogue_service_id: string;
  procedure_title_i18n: Record<string, string>;
  procedure_source: DiscoverySource;
  portal_url: string | null;
  role: DiscoveryMentionRole;
  excerpt: string;
  source_field: string;
  artifact_id: string | null;
  artifact: DiscoveryMentionArtifact | null;
  extractor: string;
  extractor_version: string;
  /** When the document applies ("bei Zuzug aus dem Ausland"), as the page states it. */
  condition: string | null;
  is_optional: boolean | null;
  category_codes: string[];
  pvog_leaf_code: string | null;
  direct_category_confidence: number | null;
  pvog_source_path: PvogSourcePath | null;
  pvog_mapping_version: string | null;
  created_at: string;
};

/** How many procedures carry a tag code, and whether an emit would use it. */
export type DiscoveryTagSupport = {
  code: string;
  procedures: number;
  /** Share of the candidate's tagged procedures, from 0 to 1. */
  share: number;
  accepted: boolean;
};

export type DiscoveryCandidateDetailResponse = {
  candidate: DiscoveryCandidateRecord;
  jurisdiction_name_i18n: Record<string, string>;
  mentions: DiscoveryCandidateMention[];
  suggested_category_codes: DiscoveryTagSupport[];
};

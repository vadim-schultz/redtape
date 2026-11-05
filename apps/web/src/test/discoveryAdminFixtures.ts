import type {
  DiscoveryCandidateEdge,
  DiscoveryCandidateMention,
  DiscoveryTagSupport,
} from "../features/discovery-admin/types";

/** A mention as the candidate detail route returns it; override what a test cares about. */
export function mention(
  overrides: Partial<DiscoveryCandidateMention> = {},
): DiscoveryCandidateMention {
  return {
    id: "m-1",
    catalogue_service_id: "cat-1",
    procedure_title_i18n: { en: "Apply for an ID card" },
    procedure_source: "pvog",
    portal_url: "https://example.gov/service/1",
    role: "required",
    excerpt: "Bitte Geburtsurkunde mitbringen",
    source_field: "details[0]",
    artifact_id: null,
    artifact: null,
    extractor: "pvog-payload",
    extractor_version: "1",
    condition: null,
    is_optional: null,
    category_codes: [],
    unknown_category_codes: [],
    pvog_leaf_code: null,
    direct_category_confidence: null,
    pvog_source_path: null,
    pvog_mapping_version: null,
    created_at: "2026-10-26T12:00:00Z",
    ...overrides,
  };
}

/** A tag code with its support, not accepted unless a test says so. */
export function tag(
  overrides: Partial<DiscoveryTagSupport> = {},
): DiscoveryTagSupport {
  return {
    code: "housing",
    procedures: 3,
    share: 0.75,
    accepted: false,
    ...overrides,
  };
}

/** An explicit edge from `parent-1` to `required-1`; override what a test cares about. */
export function edge(
  overrides: Partial<DiscoveryCandidateEdge> = {},
): DiscoveryCandidateEdge {
  return {
    id: "e-1",
    parent_candidate_id: "parent-1",
    parent_title_i18n: { de: "Personalausweis" },
    required_candidate_id: "required-1",
    required_title_i18n: { de: "Geburtsurkunde" },
    catalogue_service_id: "cat-1",
    procedure_title_i18n: { en: "Apply for an ID card" },
    basis: "explicit",
    condition: null,
    is_optional: null,
    excerpt: "Bitte Geburtsurkunde mitbringen",
    extractor: "llm",
    extractor_version: "ext-4",
    created_at: "2026-10-26T12:00:00Z",
    ...overrides,
  };
}

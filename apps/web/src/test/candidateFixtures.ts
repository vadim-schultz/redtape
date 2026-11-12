import type {
  CandidateCard,
  CandidateDetail,
  CandidateNeighbour,
  CandidateSource,
} from "../features/candidates/types";
import type { CompletenessFlags } from "../components/data-display/CompletenessChips/types";
import type {
  TranslationSummary,
  TranslationText,
} from "../services/candidateTranslationApi";
import type { DocumentTranslationRead } from "../types/documentTranslation";

export const ALL_FLAGS: CompletenessFlags = {
  has_category: true,
  has_edges: true,
  has_snapshot: true,
  has_screenshot: true,
};

/** A complete candidate card as the public API returns it; override what a test needs. */
export function candidateFixture(
  overrides: Partial<CandidateCard> = {},
): CandidateCard {
  return {
    id: "c1",
    key: "passport",
    title: "Passport",
    description: "Proof of identity.",
    description_source: "Apply for a passport",
    categories: [
      {
        code: "identity-and-documents",
        name: "Identity",
        confidence: 0.8,
      },
    ],
    mention_count: 3,
    confidence: 0.8,
    ...overrides,
  };
}

/** The list envelope of the public candidate API. */
export function candidatePage(
  items: CandidateCard[],
  total = items.length,
  offset = 0,
) {
  return { items, total, offset, limit: 20 };
}

/** One ingress or egress neighbour as the detail endpoint returns it. */
export function neighbourFixture(
  overrides: Partial<CandidateNeighbour> = {},
): CandidateNeighbour {
  return {
    id: "n1",
    title: "Birth certificate",
    description: "Issued by the registry office.",
    condition: null,
    is_optional: false,
    excerpt: "Please bring your birth certificate.",
    basis: "explicit",
    procedure_title: "Apply for a passport",
    ...overrides,
  };
}

/** One source page of a candidate. */
export function sourceFixture(
  overrides: Partial<CandidateSource> = {},
): CandidateSource {
  return {
    procedure_title: "Apply for a passport",
    portal_url: "https://portal.example/passport",
    role: "required",
    excerpt: "A valid passport is required.",
    condition: null,
    is_optional: false,
    ...overrides,
  };
}

/** A fully described candidate detail; override what a test needs. */
export function candidateDetailFixture(
  overrides: Partial<CandidateDetail> = {},
): CandidateDetail {
  return {
    ...candidateFixture(),
    ingress: [],
    ingress_truncated: false,
    egress: [],
    egress_truncated: false,
    sources: [sourceFixture()],
    screenshot: { url: "/shot", fetched_at: "2026-10-01T10:00:00Z" },
    ...overrides,
  };
}

/** The summary a card carries when a Turkish translation is stored and current. */
export function translationSummaryFixture(
  overrides: Partial<TranslationSummary> = {},
): TranslationSummary {
  return { locale: "tr", source: "mt", stale: false, ...overrides };
}

/** The stored text the translation endpoint returns. */
export function translationTextFixture(
  overrides: Partial<TranslationText> = {},
): TranslationText {
  return {
    ...translationSummaryFixture(),
    title: "Pasaport başvurusu",
    description: "Kimlik kanıtı.",
    engine: "llm",
    ...overrides,
  };
}

/** A translated procedure page as the document route returns it: ordered blocks, one untranslated list item and one untranslated row. */
export function documentTranslationFixture(
  overrides: Partial<DocumentTranslationRead> = {},
): DocumentTranslationRead {
  return {
    locale: "en",
    source_url: "https://portal.example/passport-page",
    truncated: false,
    stale: false,
    blocks: [
      { kind: "h2", text: "Required documents", untranslated: false },
      {
        kind: "p",
        text: "Proof of identity is required.",
        untranslated: false,
      },
      { kind: "li", text: "Birth certificate", untranslated: false },
      { kind: "li", text: "Reisepass gültig bis 2030", untranslated: true },
      { kind: "row", cells: ["Fee", "Validity"], untranslated: true },
      { kind: "dt", text: "Processing time", untranslated: false },
    ],
    ...overrides,
  };
}

import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { fallbackBundle, flatten, type Nested } from "./index";

function readSeed(locale: string): Record<string, string> {
  const file = resolve(
    __dirname,
    `../../../../api/scripts/seed_data/translations/${locale}.json`,
  );
  return flatten(JSON.parse(readFileSync(file, "utf8")) as Nested);
}

const SEED_DIR = resolve(
  __dirname,
  "../../../../api/scripts/seed_data/translations",
);

/** Locale files of the API seed; `review.json` is the review manifest, not a locale. */
const SEED_LOCALES = readdirSync(SEED_DIR)
  .filter((name) => name.endsWith(".json") && name !== "review.json")
  .map((name) => name.replace(".json", ""));

describe("mirrored locale files", () => {
  it("has a seed file for the two bundled locales", () => {
    expect(SEED_LOCALES).toEqual(expect.arrayContaining(["de", "en"]));
  });

  it.each(SEED_LOCALES)(
    "mirrors the API seed file of %s byte for byte",
    (locale) => {
      const seed = readFileSync(resolve(SEED_DIR, `${locale}.json`), "utf8");
      const mirror = readFileSync(resolve(__dirname, `${locale}.json`), "utf8");

      expect(mirror).toBe(seed);
    },
  );

  it("has no locale file here that the API seed lacks", () => {
    const mirrored = readdirSync(__dirname)
      .filter((name) => name.endsWith(".json"))
      .map((name) => name.replace(".json", ""));

    expect(mirrored.sort()).toEqual([...SEED_LOCALES].sort());
  });
});

const CANDIDATE_KEYS = [
  "from_source",
  "flag_category",
  "flag_edges",
  "flag_snapshot",
  "flag_screenshot",
  "flag_present",
  "flag_missing",
  "ingress",
  "ingress_empty",
  "egress",
  "egress_empty",
  "optional",
  "condition_label",
  "evidence",
  "screenshot_alt",
  "screenshot_missing",
  "screenshot_fetched",
  "sources",
  "source_role_required",
  "source_role_form",
  "source_role_issued",
  "flow",
  "flow_summary",
  "flow_empty",
  "flow_more",
  "back_to_list",
  "not_found_title",
];

/** Strings only the retired /candidates list and its menu link read. */
const RETIRED_CANDIDATE_KEYS = [
  "nav.candidates",
  ...[
    "title",
    "subtitle",
    "search_label",
    "complete_only",
    "clear_filters",
    "count_one",
    "count_other",
    "empty_title",
    "empty_description",
    "empty_filtered_description",
  ].map((key) => `candidates.${key}`),
];

describe("fallback translation bundles", () => {
  it.each(["en", "de"])("matches the API seed for %s", (locale) => {
    expect(fallbackBundle(locale)).toEqual(readSeed(locale));
  });

  it.each(["en", "de"])("has no matrix keys for %s", (locale) => {
    const keys = Object.keys(fallbackBundle(locale));

    expect(keys.filter((key) => /matrix/i.test(key))).toEqual([]);
  });

  it.each([
    ["en", "Menu"],
    ["de", "Menü"],
  ])("has common.menu for %s", (locale, label) => {
    expect(fallbackBundle(locale)["common.menu"]).toBe(label);
  });

  it("falls back to English for unknown locales", () => {
    expect(fallbackBundle("fr")).toEqual(fallbackBundle("en"));
  });

  it("has every auth.* key in both fallback bundles", () => {
    const authKeys = (locale: string) =>
      Object.keys(fallbackBundle(locale))
        .filter((key) => key.startsWith("auth."))
        .sort();

    const enKeys = authKeys("en");
    expect(enKeys.length).toBeGreaterThan(0);
    expect(authKeys("de")).toEqual(enKeys);
  });

  it.each(["en", "de"])("auth.password no longer exists for %s", (locale) => {
    expect(fallbackBundle(locale)).not.toHaveProperty("auth.password");
  });

  it("has every suggest.* key in both fallback bundles", () => {
    const suggestKeys = (locale: string) =>
      Object.keys(fallbackBundle(locale))
        .filter((key) => key.startsWith("suggest."))
        .sort();

    const enKeys = suggestKeys("en");
    expect(enKeys.length).toBeGreaterThan(0);
    expect(suggestKeys("de")).toEqual(enKeys);
  });

  it("has every suggestions.* key in both fallback bundles", () => {
    const suggestionsKeys = (locale: string) =>
      Object.keys(fallbackBundle(locale))
        .filter((key) => key.startsWith("suggestions."))
        .sort();

    const enKeys = suggestionsKeys("en");
    expect(enKeys.length).toBeGreaterThan(0);
    expect(suggestionsKeys("de")).toEqual(enKeys);
  });

  it.each(["en", "de"])("resolves every candidates key for %s", (locale) => {
    const bundle = fallbackBundle(locale);

    for (const key of CANDIDATE_KEYS) {
      expect(bundle[`candidates.${key}`], key).toBeTruthy();
    }
  });

  it.each(["en", "de"])(
    "drops the candidates list strings and the menu link label for %s",
    (locale) => {
      const bundle = fallbackBundle(locale);

      for (const key of RETIRED_CANDIDATE_KEYS) {
        expect(bundle, key).not.toHaveProperty(key);
      }
    },
  );

  it("has every candidates.* key in both fallback bundles", () => {
    const candidateKeys = (locale: string) =>
      Object.keys(fallbackBundle(locale))
        .filter((key) => key.startsWith("candidates."))
        .sort();

    expect(candidateKeys("en")).toHaveLength(CANDIDATE_KEYS.length);
    expect(candidateKeys("de")).toEqual(candidateKeys("en"));
  });

  it.each([
    ["en", "Documents you need first", "Documents that need this one"],
    [
      "de",
      "Dokumente, die du zuerst brauchst",
      "Dokumente, die dieses Dokument brauchen",
    ],
  ])(
    "candidates.ingress and candidates.egress are the plain-language headings for %s",
    (locale, ingress, egress) => {
      const bundle = fallbackBundle(locale);

      expect(bundle["candidates.ingress"]).toBe(ingress);
      expect(bundle["candidates.egress"]).toBe(egress);
    },
  );

  it.each(["en", "de"])(
    "drops the ingress_subtitle and egress_subtitle keys for %s",
    (locale) => {
      const bundle = fallbackBundle(locale);

      expect(bundle).not.toHaveProperty("candidates.ingress_subtitle");
      expect(bundle).not.toHaveProperty("candidates.egress_subtitle");
    },
  );

  it("has every discovery_admin.* key in both fallback bundles", () => {
    const adminKeys = (locale: string) =>
      Object.keys(fallbackBundle(locale))
        .filter((key) => key.startsWith("discovery_admin."))
        .sort();

    expect(adminKeys("de")).toEqual(adminKeys("en"));
  });
});

const ARTIFACT_KEYS = [
  "title",
  "empty",
  "storage_unconfigured",
  "link_unavailable",
  "kind_html_snapshot",
  "kind_screenshot",
  "download",
  "screenshot_alt",
  "col_size",
  "col_fetched",
  "col_host",
  "col_download",
  "stored_total",
  "stored_of_cap",
  "stored_nearly_full",
  "col_resource",
  "col_usage",
  "col_status",
  "budgets_title",
  "budgets_error",
  "budget_usage",
  "budget_exhausted",
  "budget_r2_class_a",
  "budget_r2_class_b",
  "budget_browser_seconds",
  "budget_neurons",
  "budget_actions_minutes",
  "budget_azure_translator_chars",
  "budget_stored_bytes",
  "translator_title",
  "translator_missing",
].map((key) => `discovery_admin.artifacts.${key}`);

const TRANSLATION_COVERAGE_KEYS = [
  "translation_title",
  "translation_denominator",
  "translation_error",
  "col_locale",
  "col_translated",
  "col_stale",
  "col_pending",
  "col_claimed",
  "col_failed",
].map((key) => `discovery_admin.coverage.${key}`);

const NOTE_KEYS = ["login_wall", "oversize", "no_mentions", "no_extractor"].map(
  (note) => `discovery_admin.tasks.note_${note}`,
);

describe("discovery admin artifact strings", () => {
  it.each(["en", "de"])("all strings resolve in %s", (locale) => {
    const bundle = fallbackBundle(locale);

    for (const key of [
      ...ARTIFACT_KEYS,
      ...NOTE_KEYS,
      ...TRANSLATION_COVERAGE_KEYS,
    ]) {
      expect(bundle[key], key).toBeTruthy();
    }
  });

  it("translates the artifact strings instead of copying English", () => {
    const en = fallbackBundle("en");
    const de = fallbackBundle("de");

    expect(de["discovery_admin.artifacts.empty"]).not.toBe(
      en["discovery_admin.artifacts.empty"],
    );
  });
});

const DOCUMENT_KEYS = [
  "documents.role_issued",
  "document.col_condition",
  "document.col_taxonomy_diagnostics",
  "document.unknown_category_codes",
  "document.optional",
  ...["title", "categories", "support", "empty", "accepted"].map(
    (key) => `document.tags.${key}`,
  ),
  ...[
    "title",
    "requires",
    "required_by",
    "empty",
    "basis_explicit",
    "basis_derived_single_issued",
    "procedure",
  ].map((key) => `document.edges.${key}`),
  ...["title", "extracted", "no_documents", "login_wall", "no_content"].map(
    (key) => `coverage.llm.${key}`,
  ),
  "tasks.note_no_content",
  "tasks.note_no_documents",
].map((key) => `discovery_admin.${key}`);

describe("discovery admin extraction strings", () => {
  it.each(["en", "de"])("all new strings resolve in %s", (locale) => {
    const bundle = fallbackBundle(locale);

    for (const key of DOCUMENT_KEYS) {
      expect(bundle[key], key).toBeTruthy();
    }
  });

  it("translates the extraction strings instead of copying English", () => {
    const en = fallbackBundle("en");
    const de = fallbackBundle("de");

    expect(de["discovery_admin.document.tags.empty"]).not.toBe(
      en["discovery_admin.document.tags.empty"],
    );
  });
});

const EMPTY_STATE_KEYS = ["ingress_empty", "egress_empty", "flow_empty"].map(
  (key) => `candidates.${key}`,
);

const STAGED_WORDING = /staged|vorgemerkt|hinterlegt/i;

describe("candidate empty states", () => {
  it.each(["en", "de"])(
    "carry no staged wording in the fallback or the API seed for %s",
    (locale) => {
      const bundle = fallbackBundle(locale);
      const seed = readSeed(locale);

      for (const key of EMPTY_STATE_KEYS) {
        expect(bundle[key], key).toBeTruthy();
        expect(bundle[key], key).not.toMatch(STAGED_WORDING);
        expect(seed[key], key).not.toMatch(STAGED_WORDING);
      }
    },
  );
});

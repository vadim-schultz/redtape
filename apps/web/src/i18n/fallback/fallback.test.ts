import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { fallbackBundle } from "./index";

type Nested = { [key: string]: string | Nested };

function flatten(tree: Nested, prefix = ""): Record<string, string> {
  return Object.entries(tree).reduce<Record<string, string>>(
    (acc, [key, value]) => {
      const path = prefix ? `${prefix}.${key}` : key;
      return typeof value === "string"
        ? { ...acc, [path]: value }
        : { ...acc, ...flatten(value, path) };
    },
    {},
  );
}

function readSeed(locale: string): Record<string, string> {
  const file = resolve(
    __dirname,
    `../../../../api/scripts/seed_data/translations/${locale}.json`,
  );
  return flatten(JSON.parse(readFileSync(file, "utf8")) as Nested);
}

const CANDIDATE_KEYS = [
  "title",
  "subtitle",
  "banner_title",
  "banner_body",
  "search_label",
  "filter_domain",
  "filter_situation",
  "complete_only",
  "clear_filters",
  "count_one",
  "count_other",
  "empty_title",
  "empty_description",
  "empty_filtered_description",
  "flag_domain",
  "flag_situation",
  "flag_edges",
  "flag_snapshot",
  "flag_screenshot",
  "flag_present",
  "flag_missing",
  "from_source",
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
  "checklist_title",
  "checklist_count",
  "flow",
  "flow_summary",
  "flow_empty",
  "flow_more",
  "back_to_list",
  "not_found_title",
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
    expect(bundle["nav.candidates"]).toBeTruthy();
  });

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
  "budget_stored_bytes",
].map((key) => `discovery_admin.artifacts.${key}`);

const NOTE_KEYS = ["login_wall", "oversize", "no_mentions", "no_extractor"].map(
  (note) => `discovery_admin.tasks.note_${note}`,
);

describe("discovery admin artifact strings", () => {
  it.each(["en", "de"])("all strings resolve in %s", (locale) => {
    const bundle = fallbackBundle(locale);

    for (const key of [...ARTIFACT_KEYS, ...NOTE_KEYS]) {
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
  "document.optional",
  ...["title", "domains", "situations", "support", "empty", "accepted"].map(
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

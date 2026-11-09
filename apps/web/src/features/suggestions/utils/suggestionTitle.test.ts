import { expect, it } from "vitest";

import type { SuggestionRead } from "../types";
import { suggestionTitle } from "./suggestionTitle";

const base = {
  id: "s1",
  status: "pending" as const,
  source_type: "human" as const,
  jurisdiction_id: "j1",
  source_url: null,
  submitted_by: { kind: "user" as const, display_name: "Ada" },
  created_at: "2026-09-28T12:00:00Z",
};

it("suggestionTitle · new_document uses the locale title", () => {
  const suggestion: SuggestionRead = {
    ...base,
    kind: "new_document",
    payload: {
      title_i18n: { en: "Residency permit", de: "Aufenthaltstitel" },
      official_url: "https://example.gov",
      category_codes: [],
    },
  };

  expect(suggestionTitle(suggestion, "de")).toBe("Aufenthaltstitel");
});

it("suggestionTitle · new_document falls back to any available locale", () => {
  const suggestion: SuggestionRead = {
    ...base,
    kind: "new_document",
    payload: {
      title_i18n: { en: "Residency permit" },
      official_url: "https://example.gov",
      category_codes: [],
    },
  };

  expect(suggestionTitle(suggestion, "de")).toBe("Residency permit");
});

it("suggestionTitle · new_requirement joins parent and required ids with an arrow", () => {
  const suggestion: SuggestionRead = {
    ...base,
    kind: "new_requirement",
    payload: {
      parent_document_id: "doc-parent",
      required_document_id: "doc-required",
    },
  };

  expect(suggestionTitle(suggestion, "en")).toBe("doc-parent → doc-required");
});

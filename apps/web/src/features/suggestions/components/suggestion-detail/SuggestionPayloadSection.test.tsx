import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { SuggestionRead } from "../../types";
import SuggestionPayloadSection from "./SuggestionPayloadSection";

const newDocumentSuggestion: SuggestionRead = {
  id: "s1",
  kind: "new_document",
  status: "pending",
  source_type: "human",
  jurisdiction_id: "j1",
  payload: {
    title_i18n: { en: "Residency permit" },
    description_i18n: { en: "Register your address" },
    official_url: "https://example.gov/residency",
    domain_codes: [],
    situation_codes: [],
  },
  source_url: null,
  submitted_by: { kind: "user", display_name: "Ada" },
  created_at: "2026-09-28T11:00:00Z",
};

const newRequirementSuggestion: SuggestionRead = {
  ...newDocumentSuggestion,
  kind: "new_requirement",
  payload: {
    parent_document_id: "doc-parent",
    required_document_id: "doc-required",
  },
};

it("SuggestionPayloadSection · new_document links the official URL", async () => {
  renderWithProviders(
    <SuggestionPayloadSection suggestion={newDocumentSuggestion} />,
  );

  const link = await screen.findByRole("link", {
    name: "https://example.gov/residency",
  });
  expect(link).toHaveAttribute("href", "https://example.gov/residency");
  expect(screen.getByText("Register your address")).toBeInTheDocument();
});

it("SuggestionPayloadSection · new_requirement links both documents", async () => {
  renderWithProviders(
    <SuggestionPayloadSection suggestion={newRequirementSuggestion} />,
  );

  const links = await screen.findAllByRole("link");
  expect(links).toHaveLength(2);
  expect(links[0]).toHaveAttribute("href", "/documents/doc-parent");
  expect(links[1]).toHaveAttribute("href", "/documents/doc-required");
});

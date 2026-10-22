import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { SuggestionRead } from "../../types";
import SuggestionCard from "./SuggestionCard";

const now = new Date("2026-09-28T12:00:00Z");

const newDocumentSuggestion: SuggestionRead = {
  id: "s1",
  kind: "new_document",
  status: "pending",
  source_type: "human",
  jurisdiction_id: "j1",
  payload: {
    title_i18n: { en: "Residency permit" },
    official_url: "https://example.gov",
    domain_codes: [],
    situation_codes: [],
  },
  source_url: null,
  submitted_by: { kind: "user", display_name: "Ada" },
  created_at: new Date("2026-09-28T11:00:00Z").toISOString(),
};

it("SuggestionCard · renders the title inside a linked card", async () => {
  renderWithProviders(
    <SuggestionCard suggestion={newDocumentSuggestion} now={now} />,
  );

  const link = await screen.findByRole("link");
  expect(link).toHaveAttribute("href", "/suggestions/s1");
  expect(
    screen.getByRole("heading", { name: "Residency permit" }),
  ).toBeInTheDocument();
});

it("SuggestionCard · shows the crawler badge for a crawler source", async () => {
  renderWithProviders(
    <SuggestionCard
      suggestion={{
        ...newDocumentSuggestion,
        submitted_by: { kind: "crawler", display_name: "crawler-de-federal" },
      }}
      now={now}
    />,
  );

  expect(await screen.findByText("Crawler")).toBeInTheDocument();
});

it("SuggestionCard · shows the person badge for a human source", async () => {
  renderWithProviders(
    <SuggestionCard suggestion={newDocumentSuggestion} now={now} />,
  );

  expect(await screen.findByText("Person")).toBeInTheDocument();
});

it("SuggestionCard · shows the requirement arrow for an edge suggestion", async () => {
  renderWithProviders(
    <SuggestionCard
      suggestion={{
        ...newDocumentSuggestion,
        kind: "new_requirement",
        payload: {
          parent_document_id: "doc-parent",
          required_document_id: "doc-required",
        },
      }}
      now={now}
    />,
  );

  expect(
    await screen.findByText("doc-parent → doc-required"),
  ).toBeInTheDocument();
});

it("SuggestionCard · shows the status badge", async () => {
  renderWithProviders(
    <SuggestionCard
      suggestion={{ ...newDocumentSuggestion, status: "approved" }}
      now={now}
    />,
  );

  expect(await screen.findByText("Approved")).toBeInTheDocument();
});

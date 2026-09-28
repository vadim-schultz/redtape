import { screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { SuggestionRead } from "../../types";
import SuggestionsListQueryStatus from "./SuggestionsListQueryStatus";

const suggestions: SuggestionRead[] = [
  {
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
    created_at: "2026-09-28T11:00:00Z",
  },
  {
    id: "s2",
    kind: "new_document",
    status: "pending",
    source_type: "crawler",
    jurisdiction_id: "j1",
    payload: {
      title_i18n: { en: "Passport renewal" },
      official_url: "https://example.gov",
      domain_codes: [],
      situation_codes: [],
    },
    source_url: null,
    submitted_by: { kind: "crawler", display_name: "crawler-de-federal" },
    created_at: "2026-09-28T10:00:00Z",
  },
];

it("SuggestionsListQueryStatus · loading renders skeleton not cards", () => {
  renderWithProviders(
    <SuggestionsListQueryStatus
      isLoading
      isError={false}
      error={undefined}
      onRetry={vi.fn()}
      isRefreshing={false}
      suggestions={suggestions}
    />,
  );

  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

it("SuggestionsListQueryStatus · empty list renders an empty state", () => {
  renderWithProviders(
    <SuggestionsListQueryStatus
      isLoading={false}
      isError={false}
      error={undefined}
      onRetry={vi.fn()}
      isRefreshing={false}
      suggestions={[]}
    />,
  );

  expect(screen.getByRole("status")).toHaveTextContent("No suggestions found");
});

it("SuggestionsListQueryStatus · error offers retry", async () => {
  const onRetry = vi.fn();
  const { user } = renderWithProviders(
    <SuggestionsListQueryStatus
      isLoading={false}
      isError
      error={new Error("boom")}
      onRetry={onRetry}
      isRefreshing={false}
      suggestions={undefined}
    />,
  );

  await user.click(await screen.findByRole("button", { name: "Try again" }));
  expect(onRetry).toHaveBeenCalledOnce();
});

it("SuggestionsListQueryStatus · populated list renders count and cards", async () => {
  renderWithProviders(
    <SuggestionsListQueryStatus
      isLoading={false}
      isError={false}
      error={undefined}
      onRetry={vi.fn()}
      isRefreshing={false}
      suggestions={suggestions}
    />,
  );

  expect(await screen.findByText("2 suggestions")).toBeInTheDocument();
  expect(screen.getAllByRole("link")).toHaveLength(2);
});

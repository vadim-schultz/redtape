import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import SuggestionsListPage from "./SuggestionsListPage";

const fetchMock = vi.fn();

const suggestion = (overrides: Partial<Record<string, unknown>> = {}) => ({
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
  ...overrides,
});

function respondWith(items: unknown[]) {
  fetchMock.mockImplementation(async (url: string) => {
    const parsed = new URL(String(url));
    if (parsed.pathname.endsWith("/api/v1/suggestions"))
      return new Response(
        JSON.stringify({ items, total: items.length, offset: 0, limit: 20 }),
      );
    return new Response(JSON.stringify({ items: [] }));
  });
}

function suggestionsCalls(): URL[] {
  return fetchMock.mock.calls
    .map(([url]) => new URL(String(url)))
    .filter((url) => url.pathname.endsWith("/api/v1/suggestions"));
}

beforeEach(() => {
  window.localStorage.setItem("locale", "en");
  vi.stubGlobal("fetch", fetchMock);
  respondWith([suggestion()]);
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

it("SuggestionsListPage · defaults to pending and shows cards", async () => {
  renderWithProviders(<SuggestionsListPage />);

  await waitFor(() => expect(suggestionsCalls()).not.toHaveLength(0));
  expect(suggestionsCalls()[0].searchParams.getAll("status")).toEqual([
    "pending",
  ]);
  expect(await screen.findByText("Residency permit")).toBeInTheDocument();
});

it("SuggestionsListPage · switching to Approved refetches with that status", async () => {
  const { user } = renderWithProviders(<SuggestionsListPage />);
  await screen.findByText("Residency permit");

  await user.click(screen.getByRole("button", { name: "Approved" }));

  await waitFor(() =>
    expect(suggestionsCalls().at(-1)?.searchParams.getAll("status")).toEqual([
      "approved",
    ]),
  );
});

it("SuggestionsListPage · shows an empty state for no results", async () => {
  respondWith([]);
  renderWithProviders(<SuggestionsListPage />);

  expect(await screen.findByText("No suggestions found")).toBeInTheDocument();
});

it("SuggestionsListPage · a bad ?status= requests pending", async () => {
  renderWithProviders(<SuggestionsListPage />, {
    initialEntries: ["/suggestions?status=bogus"],
  });

  await waitFor(() => expect(suggestionsCalls()).not.toHaveLength(0));
  expect(suggestionsCalls()[0].searchParams.getAll("status")).toEqual([
    "pending",
  ]);
});

it("SuggestionsListPage · shows a query-error state", async () => {
  fetchMock.mockResolvedValue(new Response("boom", { status: 500 }));
  renderWithProviders(<SuggestionsListPage />);

  expect(
    await screen.findByText("Server error. Please try again later."),
  ).toBeInTheDocument();
});

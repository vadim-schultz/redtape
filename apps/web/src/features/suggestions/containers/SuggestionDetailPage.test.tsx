import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import SuggestionDetailPage from "./SuggestionDetailPage";

const fetchMock = vi.fn();

beforeEach(() => {
  window.localStorage.setItem("locale", "en");
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

function respondWith(body: unknown, status = 200) {
  fetchMock.mockResolvedValue(new Response(JSON.stringify(body), { status }));
}

function renderAt(path: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/suggestions/:id" element={<SuggestionDetailPage />} />
    </Routes>,
    { initialEntries: [path] },
  );
}

it("SuggestionDetailPage · renders a new_document payload with a working official URL link", async () => {
  respondWith({
    id: "s1",
    kind: "new_document",
    status: "pending",
    source_type: "human",
    jurisdiction_id: "j1",
    payload: {
      title_i18n: { en: "Residency permit" },
      official_url: "https://example.gov/residency",
      domain_codes: [],
      situation_codes: [],
    },
    source_url: null,
    submitted_by: { kind: "user", display_name: "Ada" },
    created_at: "2026-09-28T11:00:00Z",
  });

  renderAt("/suggestions/s1");

  const link = await screen.findByRole("link", {
    name: "https://example.gov/residency",
  });
  expect(link).toHaveAttribute("href", "https://example.gov/residency");
});

it("SuggestionDetailPage · renders a new_requirement payload with both documents linked", async () => {
  respondWith({
    id: "s2",
    kind: "new_requirement",
    status: "pending",
    source_type: "human",
    jurisdiction_id: "j1",
    payload: {
      parent_document_id: "doc-parent",
      required_document_id: "doc-required",
    },
    source_url: null,
    submitted_by: { kind: "user", display_name: "Ada" },
    created_at: "2026-09-28T11:00:00Z",
  });

  renderAt("/suggestions/s2");

  const links = await screen.findAllByRole("link");
  expect(links.map((l) => l.getAttribute("href"))).toEqual([
    "/documents/doc-parent",
    "/documents/doc-required",
  ]);
});

it("SuggestionDetailPage · unknown id shows the not-found view", async () => {
  respondWith({ detail: "Suggestion not found" }, 404);

  renderAt("/suggestions/missing");

  expect(await screen.findByText("Suggestion not found")).toBeInTheDocument();
});

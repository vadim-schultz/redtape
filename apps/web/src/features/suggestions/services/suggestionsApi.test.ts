import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { fetchSuggestionDetail, fetchSuggestions } from "./suggestionsApi";

const fetchMock = vi.fn();

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

function requestedParams(): URLSearchParams {
  return new URL(String(fetchMock.mock.calls[0][0])).searchParams;
}

it("suggestionsApi · fetchSuggestions sends the status filter", async () => {
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ items: [], total: 0, offset: 0, limit: 20 })),
  );

  await fetchSuggestions({ locale: "en", status: ["pending"] });

  expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe(
    "/api/v1/suggestions",
  );
  expect(requestedParams().getAll("status")).toEqual(["pending"]);
});

it("suggestionsApi · fetchSuggestions sends no status param when omitted", async () => {
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ items: [], total: 0, offset: 0, limit: 20 })),
  );

  await fetchSuggestions({ locale: "en" });

  expect(requestedParams().has("status")).toBe(false);
});

it("suggestionsApi · fetchSuggestions sends kind and jurisdiction_id", async () => {
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ items: [], total: 0, offset: 0, limit: 20 })),
  );

  await fetchSuggestions({
    locale: "en",
    kind: "new_document",
    jurisdictionId: "j1",
  });

  expect(requestedParams().get("kind")).toBe("new_document");
  expect(requestedParams().get("jurisdiction_id")).toBe("j1");
});

it("suggestionsApi · fetchSuggestionDetail requests the suggestion by id", async () => {
  fetchMock.mockResolvedValue(new Response(JSON.stringify({ id: "s1" })));

  await fetchSuggestionDetail({ locale: "en", id: "s1" });

  expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe(
    "/api/v1/suggestions/s1",
  );
});

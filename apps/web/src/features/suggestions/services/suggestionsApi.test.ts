import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  createSuggestion,
  fetchSuggestionDetail,
  fetchSuggestions,
  SuggestionConflictError,
} from "./suggestionsApi";

const fetchMock = vi.fn();

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

const request = {
  municipality_code: "M1",
  payload: {
    title_i18n: { en: "Residency permit" },
    official_url: "https://example.gov/residency",
    domain_codes: [],
    situation_codes: [],
  },
};

it("suggestionsApi · createSuggestion posts the payload with the bearer token", async () => {
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ id: "s1" }), { status: 201 }),
  );

  await createSuggestion({ locale: "en", accessToken: "token-1", request });

  const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
  expect(new URL(url).pathname).toBe("/api/v1/suggestions");
  expect(init.method).toBe("POST");
  expect((init.headers as Record<string, string>).Authorization).toBe(
    "Bearer token-1",
  );
  expect(JSON.parse(init.body as string)).toEqual(request);
});

it("suggestionsApi · a 409 surfaces conflicts on the error", async () => {
  fetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        detail: "Duplicate suggestion",
        extra: { conflicts: [{ type: "document", id: "d1" }] },
      }),
      { status: 409 },
    ),
  );

  const promise = createSuggestion({
    locale: "en",
    accessToken: "token-1",
    request,
  });

  await expect(promise).rejects.toBeInstanceOf(SuggestionConflictError);
  await expect(promise).rejects.toMatchObject({
    conflicts: [{ type: "document", id: "d1" }],
  });
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

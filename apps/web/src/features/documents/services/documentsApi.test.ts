import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { candidateFixture } from "../../../test/candidateFixtures";
import { parseListUrl } from "../../../services/listQuery";
import type { DocumentListRequest } from "../types";
import { DOCUMENT_LIST_SPEC } from "./documentListQuery";
import { fetchDocuments } from "./documentsApi";

const fetchMock = vi.fn();

function requestedUrl(): URL {
  return new URL(String(fetchMock.mock.calls[0][0]));
}

function respondWith(items: unknown[] = []) {
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ items, total: 57, offset: 20, limit: 20 })),
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  respondWith();
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

const unfiltered: DocumentListRequest = {
  categories: [],
  query: { offset: 0, limit: 20, filters: {} },
};

const fetchWith = (request: Partial<DocumentListRequest>) =>
  fetchDocuments({ locale: "en", request: { ...unfiltered, ...request } });

it("documentsApi · reads the candidate list, not the document list", async () => {
  await fetchWith({});

  expect(requestedUrl().pathname).toBe("/api/v1/candidates");
});

it("documentsApi · sends canonical category codes as a CSV filter", async () => {
  await fetchWith({ categories: ["a", "b"] });

  const params = requestedUrl().searchParams;
  expect(params.get("filter[category]")).toBe("a,b");
});

it("documentsApi · sends search and page", async () => {
  await fetchWith({
    query: { offset: 40, limit: 20, search: "ausweis", filters: {} },
  });

  const params = requestedUrl().searchParams;
  expect(params.get("q")).toBe("ausweis");
  expect(params.get("offset")).toBe("40");
  expect(params.get("limit")).toBe("20");
});

it("documents request · sends no sort_by or sort_order and still sends filter[category] as CSV", async () => {
  const stale = new URLSearchParams("sort_by=title&sort_order=desc&q=x");
  await fetchWith({
    categories: ["a", "b"],
    query: parseListUrl(stale, DOCUMENT_LIST_SPEC),
  });

  const params = requestedUrl().searchParams;
  expect(params.has("sort_by")).toBe(false);
  expect(params.has("sort_order")).toBe(false);
  expect(params.get("filter[category]")).toBe("a,b");
  expect(params.get("q")).toBe("x");
});

it("documentsApi · leaves out filters, search and sort that are not set", async () => {
  await fetchWith({});

  const names = [...requestedUrl().searchParams.keys()].sort();
  expect(names).toEqual(["limit", "offset"]);
});

it("documentsApi · sends only the bracketed canonical category filter", async () => {
  await fetchWith({ categories: ["a"] });

  const params = requestedUrl().searchParams;
  expect(params.has("municipality_code")).toBe(false);
  expect(params.get("filter[category]")).toBe("a");
});

it("documentsApi · maps a candidate card to a document with tags and confidence", async () => {
  respondWith([
    candidateFixture({
      id: "c9",
      title: "Passport",
      description: "Proof of identity.",
      confidence: 0.8,
      categories: [
        { code: "identity", name: "Identity", confidence: 0.4 },
        { code: "moving", name: "Moving", confidence: 0.9 },
        { code: "work", name: "Work", confidence: 0.1 },
      ],
    }),
  ]);

  const page = await fetchWith({});

  expect(page).toMatchObject({ total: 57, offset: 20, limit: 20 });
  expect(page.items).toEqual([
    {
      id: "c9",
      title: "Passport",
      description: "Proof of identity.",
      confidence: 0.8,
      similarity: null,
      translation: null,
      tags: [
        { code: "moving", name: "Moving", confidence: 0.9 },
        { code: "identity", name: "Identity", confidence: 0.4 },
        { code: "work", name: "Work", confidence: 0.1 },
      ],
    },
  ]);
});

it("documentsApi · a card without categories maps to no tags", async () => {
  respondWith([candidateFixture({ categories: [] })]);

  const page = await fetchWith({});

  expect(page.items[0].tags).toEqual([]);
});

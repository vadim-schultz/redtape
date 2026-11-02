import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { candidateFixture } from "../../../test/candidateFixtures";
import type { DocumentListRequest } from "../types";
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
  domains: [],
  situations: [],
  query: { offset: 0, limit: 20, filters: {} },
};

const fetchWith = (request: Partial<DocumentListRequest>) =>
  fetchDocuments({ locale: "en", request: { ...unfiltered, ...request } });

it("documentsApi · reads the candidate list, not the document list", async () => {
  await fetchWith({});

  expect(requestedUrl().pathname).toBe("/api/v1/candidates");
});

it("documentsApi · sends the selected codes as CSV filters", async () => {
  await fetchWith({ domains: ["a", "b"], situations: ["x", "y"] });

  const params = requestedUrl().searchParams;
  expect(params.get("filter[domain]")).toBe("a,b");
  expect(params.get("filter[situation]")).toBe("x,y");
});

it("documentsApi · sends search, sort and page", async () => {
  await fetchWith({
    query: {
      offset: 40,
      limit: 20,
      search: "ausweis",
      sortBy: "title",
      sortOrder: "desc",
      filters: {},
    },
  });

  const params = requestedUrl().searchParams;
  expect(params.get("q")).toBe("ausweis");
  expect(params.get("sort_by")).toBe("title");
  expect(params.get("sort_order")).toBe("desc");
  expect(params.get("offset")).toBe("40");
  expect(params.get("limit")).toBe("20");
});

it("documentsApi · leaves out filters, search and sort that are not set", async () => {
  await fetchWith({});

  const names = [...requestedUrl().searchParams.keys()].sort();
  expect(names).toEqual(["limit", "offset"]);
});

it("documentsApi · never sends a jurisdiction or the old repeated params", async () => {
  await fetchWith({ domains: ["a"], situations: ["x"] });

  const params = requestedUrl().searchParams;
  expect(params.has("municipality_code")).toBe(false);
  expect(params.has("domain")).toBe(false);
  expect(params.has("situation")).toBe(false);
});

it("documentsApi · maps a candidate card to a document with tags and confidence", async () => {
  respondWith([
    candidateFixture({
      id: "c9",
      title: "Passport",
      description: "Proof of identity.",
      confidence: 0.8,
      domains: [{ code: "identity", name: "Identity", confidence: 0.4 }],
      situations: [
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
      tags: [
        { axis: "situation", code: "moving", name: "Moving", confidence: 0.9 },
        { axis: "domain", code: "identity", name: "Identity", confidence: 0.4 },
        { axis: "situation", code: "work", name: "Work", confidence: 0.1 },
      ],
    },
  ]);
});

it("documentsApi · a card without tags maps to a document with no tags", async () => {
  respondWith([candidateFixture({ domains: [], situations: [] })]);

  const page = await fetchWith({});

  expect(page.items[0].tags).toEqual([]);
});

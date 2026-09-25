import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { fetchDomains, fetchMatrix } from "./taxonomyApi";

const fetchMock = vi.fn();

function respondWith(body: unknown) {
  fetchMock.mockResolvedValue(new Response(JSON.stringify(body)));
}

function requestedUrl(): URL {
  return new URL(String(fetchMock.mock.calls[0][0]));
}

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

it("taxonomyApi · fetchDomains calls /api/v1/domains with locale", async () => {
  respondWith([]);

  await fetchDomains("de");

  expect(requestedUrl().pathname).toBe("/api/v1/domains");
  expect(fetchMock.mock.calls[0][1].headers["Accept-Language"]).toBe("de");
});

it("taxonomyApi · fetchMatrix sends municipality_code when scoped", async () => {
  respondWith({});

  await fetchMatrix({ locale: "en", municipalityCode: "M1" });

  expect(requestedUrl().pathname).toBe("/api/v1/matrix");
  expect(requestedUrl().searchParams.get("municipality_code")).toBe("M1");
});

it("taxonomyApi · fetchMatrix omits the param when unscoped", async () => {
  respondWith({});

  await fetchMatrix({ locale: "en", municipalityCode: null });

  expect(requestedUrl().searchParams.has("municipality_code")).toBe(false);
});

it("taxonomyApi · fetchMatrix returns totals unchanged", async () => {
  const body = {
    total: 7,
    cells: [{ domain: "housing", situation: "moving-house", count: 3 }],
    situations: [{ code: "moving-house", count: 5 }],
    domains: [{ code: "housing", count: 4 }],
  };
  respondWith(body);

  const result = await fetchMatrix({ locale: "en", municipalityCode: null });

  expect(result).toEqual(body);
});

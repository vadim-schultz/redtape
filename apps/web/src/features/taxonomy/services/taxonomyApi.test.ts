import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { fetchDomains, fetchLifeSituationGroups } from "./taxonomyApi";

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

it("taxonomyApi · fetchLifeSituationGroups calls /api/v1/life-situation-groups with locale", async () => {
  respondWith([]);

  await fetchLifeSituationGroups("de");

  expect(requestedUrl().pathname).toBe("/api/v1/life-situation-groups");
  expect(fetchMock.mock.calls[0][1].headers["Accept-Language"]).toBe("de");
});

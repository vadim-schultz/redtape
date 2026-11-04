import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  fetchCategoryTree,
  fetchDomains,
  fetchLifeSituationGroups,
} from "./taxonomyApi";

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

it("category tree hook · returns roots and children from one query", async () => {
  const tree = [
    {
      code: "home-and-housing",
      name: "Home & housing",
      description: "",
      icon: "home",
      parent_code: null,
      children: [
        {
          code: "moving-house",
          name: "Moving house",
          description: "",
          icon: null,
          parent_code: "home-and-housing",
          children: [],
        },
      ],
    },
  ];
  respondWith(tree);

  const result = await fetchCategoryTree("en");

  expect(result).toEqual(tree);
  expect(requestedUrl().pathname).toBe("/api/v1/categories");
  expect(fetchMock.mock.calls[0][1].headers["Accept-Language"]).toBe("en");
});

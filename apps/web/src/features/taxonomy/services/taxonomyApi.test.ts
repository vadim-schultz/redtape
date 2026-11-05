import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { fetchCategoryTree } from "./taxonomyApi";

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

it("taxonomyApi · fetches the canonical category tree with locale", async () => {
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

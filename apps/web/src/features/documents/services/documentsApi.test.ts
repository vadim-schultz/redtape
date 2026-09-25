import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { fetchDocuments } from "./documentsApi";

const fetchMock = vi.fn();

function requestedParams(): URLSearchParams {
  return new URL(String(fetchMock.mock.calls[0][0])).searchParams;
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockResolvedValue(new Response(JSON.stringify({ items: [] })));
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

const unfiltered = {
  locale: "en",
  municipalityCode: null,
  domains: [],
  situations: [],
};

it("documentsApi · sends repeated domain params", async () => {
  await fetchDocuments({ ...unfiltered, domains: ["a", "b"] });

  expect(requestedParams().getAll("domain")).toEqual(["a", "b"]);
});

it("documentsApi · sends repeated situation params", async () => {
  await fetchDocuments({ ...unfiltered, situations: ["x", "y"] });

  expect(requestedParams().getAll("situation")).toEqual(["x", "y"]);
});

it("documentsApi · sends no filter params when none selected", async () => {
  await fetchDocuments(unfiltered);

  expect(requestedParams().toString()).toBe("");
});

it("documentsApi · keeps municipality_code alongside filters", async () => {
  await fetchDocuments({
    ...unfiltered,
    municipalityCode: "M1",
    domains: ["a"],
  });

  expect(requestedParams().get("municipality_code")).toBe("M1");
  expect(requestedParams().getAll("domain")).toEqual(["a"]);
});

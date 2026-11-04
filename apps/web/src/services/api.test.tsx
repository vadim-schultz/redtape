import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { apiRequest } from "./api";

const fetchMock = vi.fn();

function requestHeaders(index: number): Headers {
  const init = fetchMock.mock.calls[index][1] as RequestInit;
  return new Headers(init.headers);
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async () => new Response("{}"));
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

it("apiRequest · adds the bearer header when an access token is given", async () => {
  await apiRequest("/api/v1/documents", {
    locale: "en",
    accessToken: "token-1",
  });

  expect(requestHeaders(0).get("Authorization")).toBe("Bearer token-1");
});

it("apiRequest · sends no Authorization header without a token", async () => {
  await apiRequest("/api/v1/documents", { locale: "en" });

  expect(requestHeaders(0).has("Authorization")).toBe(false);
});

it("apiRequest · throws ApiRequestError with status and body for a non-OK response", async () => {
  fetchMock.mockImplementation(
    async () => new Response("not found", { status: 404 }),
  );

  await expect(
    apiRequest("/api/v1/documents", { locale: "en" }),
  ).rejects.toMatchObject({ status: 404, bodyText: "not found" });
});

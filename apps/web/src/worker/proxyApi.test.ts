import { afterEach, describe, expect, it, vi } from "vitest";
import { buildUpstreamRequest, isApiPath, proxyApiRequest } from "./proxyApi";

describe("isApiPath", () => {
  it("returns false for SPA routes", () => {
    expect(isApiPath("/documents")).toBe(false);
  });
});

describe("buildUpstreamRequest", () => {
  it("forwards API paths to the configured origin with hop-by-hop headers removed", () => {
    const request = new Request(
      "https://redtape-web.example.test/api/v1/locales?country=DE",
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          Origin: "https://redtape-web.example.test",
          Host: "redtape-web.example.test",
        },
      },
    );

    const upstream = buildUpstreamRequest(
      request,
      "https://redtape-api.onrender.com",
    );

    expect(upstream.url).toBe(
      "https://redtape-api.onrender.com/api/v1/locales?country=DE",
    );
    expect(upstream.method).toBe("GET");
    expect(upstream.headers.get("Accept")).toBe("application/json");
    expect(upstream.headers.get("Origin")).toBeNull();
    expect(upstream.headers.get("Host")).toBeNull();
  });
});

describe("proxyApiRequest", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the upstream response status without rewriting errors", async () => {
    const fetchMock = vi.fn(async () => new Response("nope", { status: 503 }));
    vi.stubGlobal("fetch", fetchMock);

    const request = new Request(
      "https://redtape-web.example.test/api/v1/documents",
      { method: "GET" },
    );

    const response = await proxyApiRequest(
      request,
      "https://redtape-api.onrender.com",
    );

    expect(response.status).toBe(503);
    expect(await response.text()).toBe("nope");
  });
});

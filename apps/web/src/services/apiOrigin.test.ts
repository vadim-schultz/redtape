import { afterEach, describe, expect, it, vi } from "vitest";
import { apiOrigin, buildApiUrl } from "./apiOrigin";

describe("apiOrigin", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses configured VITE_API_URL as the origin for API paths", () => {
    vi.stubEnv("VITE_API_URL", "http://localhost:8000");
    vi.stubEnv("MODE", "development");

    expect(buildApiUrl("/api/v1/documents").href).toBe(
      "http://localhost:8000/api/v1/documents",
    );
  });

  it("uses window.location.origin in production when VITE_API_URL is unset", () => {
    vi.stubEnv("VITE_API_URL", "");
    vi.stubEnv("MODE", "production");
    vi.stubGlobal("location", {
      ...window.location,
      origin: "https://redtape-web.example.test",
    });

    expect(apiOrigin()).toBe("https://redtape-web.example.test");
    expect(buildApiUrl("/api/v1/documents").href).toBe(
      "https://redtape-web.example.test/api/v1/documents",
    );
    expect(apiOrigin()).not.toBe("http://localhost:8000");
  });
});

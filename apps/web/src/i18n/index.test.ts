import { afterEach, describe, expect, it, vi } from "vitest";

import { fallbackBundle } from "./fallback";
import { createBundleLoader, loadBundle } from "./index";

afterEach(() => vi.unstubAllGlobals());

describe("bundles", () => {
  it("loads the bundled de and en without a dynamic import", async () => {
    await expect(loadBundle("de")).resolves.toEqual(fallbackBundle("de"));
    await expect(loadBundle("en")).resolves.toEqual(fallbackBundle("en"));
  });

  it("an unknown locale loads the en fallback without a network error", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadBundle("fr")).resolves.toEqual(fallbackBundle("en"));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("flattens a lazily imported locale file once the loader resolves", async () => {
    const load = createBundleLoader({
      "./fallback/tr.json": async () => ({ common: { menu: "Menü" } }),
    });

    await expect(load("tr")).resolves.toEqual({ "common.menu": "Menü" });
  });

  it("falls back to en when the lazy chunk fails to load", async () => {
    const load = createBundleLoader({
      "./fallback/tr.json": () => Promise.reject(new Error("chunk 404")),
    });

    await expect(load("tr")).resolves.toEqual(fallbackBundle("en"));
  });
});

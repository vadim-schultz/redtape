import { describe, expect, it } from "vitest";

import { hostOf } from "./hostOf";

describe("hostOf", () => {
  it("returns the host without path or query", () => {
    expect(hostOf("https://a.gov/x?q=1")).toBe("a.gov");
  });

  it("keeps an explicit port", () => {
    expect(hostOf("https://a.gov:8080/x")).toBe("a.gov:8080");
  });

  it("drops user info", () => {
    expect(hostOf("https://user:pw@a.gov/x")).toBe("a.gov");
  });

  it.each(["not a url", "mailto:a@b", "", null, undefined])(
    "returns an empty string for %j",
    (url) => {
      expect(hostOf(url)).toBe("");
    },
  );
});

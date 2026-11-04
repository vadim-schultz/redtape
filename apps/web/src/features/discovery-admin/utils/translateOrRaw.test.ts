import { describe, expect, it } from "vitest";

import { translateOrRaw } from "./translateOrRaw";

const bundle: Record<string, string> = {
  "status.open": "Offen",
  "status.empty": "",
};

const t = (key: string): string => bundle[key] ?? key;

describe("translateOrRaw", () => {
  it("returns the translation when the key resolves", () => {
    expect(translateOrRaw(t, "status.open", "open")).toBe("Offen");
  });

  it("returns raw when the translator echoes the key back", () => {
    expect(translateOrRaw(t, "status.unknown", "legacy-value")).toBe(
      "legacy-value",
    );
  });

  it("returns an empty raw value when the key is missing", () => {
    expect(translateOrRaw(t, "status.unknown", "")).toBe("");
  });

  it("returns an empty translation as is, not replaced by raw", () => {
    expect(translateOrRaw(t, "status.empty", "raw")).toBe("");
  });
});

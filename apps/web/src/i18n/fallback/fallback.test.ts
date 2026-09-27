import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { fallbackBundle } from "./index";

type Nested = { [key: string]: string | Nested };

function flatten(tree: Nested, prefix = ""): Record<string, string> {
  return Object.entries(tree).reduce<Record<string, string>>(
    (acc, [key, value]) => {
      const path = prefix ? `${prefix}.${key}` : key;
      return typeof value === "string"
        ? { ...acc, [path]: value }
        : { ...acc, ...flatten(value, path) };
    },
    {},
  );
}

function readSeed(locale: string): Record<string, string> {
  const file = resolve(
    __dirname,
    `../../../../api/scripts/seed_data/translations/${locale}.json`,
  );
  return flatten(JSON.parse(readFileSync(file, "utf8")) as Nested);
}

describe("fallback translation bundles", () => {
  it.each(["en", "de"])("matches the API seed for %s", (locale) => {
    expect(fallbackBundle(locale)).toEqual(readSeed(locale));
  });

  it.each(["en", "de"])("has no matrix keys for %s", (locale) => {
    const keys = Object.keys(fallbackBundle(locale));

    expect(keys.filter((key) => /matrix/i.test(key))).toEqual([]);
  });

  it.each([
    ["en", "Menu"],
    ["de", "Menü"],
  ])("has common.menu for %s", (locale, label) => {
    expect(fallbackBundle(locale)["common.menu"]).toBe(label);
  });

  it("falls back to English for unknown locales", () => {
    expect(fallbackBundle("fr")).toEqual(fallbackBundle("en"));
  });

  it("has every auth.* key in both fallback bundles", () => {
    const authKeys = (locale: string) =>
      Object.keys(fallbackBundle(locale))
        .filter((key) => key.startsWith("auth."))
        .sort();

    const enKeys = authKeys("en");
    expect(enKeys.length).toBeGreaterThan(0);
    expect(authKeys("de")).toEqual(enKeys);
  });

  it.each(["en", "de"])("auth.password no longer exists for %s", (locale) => {
    expect(fallbackBundle(locale)).not.toHaveProperty("auth.password");
  });
});

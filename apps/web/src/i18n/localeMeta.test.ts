import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import {
  DEFAULT_LOCALE,
  LOCALE_CODES,
  intlTag,
  isSupportedLocale,
} from "./localeMeta";

const API_LOCALE_FILE = resolve(__dirname, "../../../api/app/shared/locale.py");

/** Locale codes declared in the API's `SUPPORTED_LOCALES` tuple, in order. */
function apiLocaleCodes(source: string): string[] {
  return [...source.matchAll(/LocaleSpec\("([a-z]{2})"/g)].map((m) => m[1]);
}

/** Codes present on one side only, named by side; empty when the lists agree. */
function localeDrift(web: readonly string[], api: readonly string[]): string[] {
  return [
    ...web.filter((code) => !api.includes(code)).map((c) => `web only: ${c}`),
    ...api.filter((code) => !web.includes(code)).map((c) => `api only: ${c}`),
  ];
}

describe("localeMeta", () => {
  it("matches the API's supported locale list", () => {
    const api = apiLocaleCodes(readFileSync(API_LOCALE_FILE, "utf8"));

    expect(api.length).toBeGreaterThan(0);
    expect(localeDrift(LOCALE_CODES, api)).toEqual([]);
  });

  it("differs from the API's supported list when a locale is added on one side", () => {
    expect(localeDrift(["de", "en", "tr"], ["de", "en", "xx"])).toEqual([
      "web only: tr",
      "api only: xx",
    ]);
  });

  it("lists the seven interface languages with the default first", () => {
    expect(LOCALE_CODES).toEqual(["de", "en", "tr", "ru", "uk", "pl", "ro"]);
    expect(DEFAULT_LOCALE).toBe(LOCALE_CODES[0]);
  });

  it("accepts a supported code and rejects fr, empty and null", () => {
    expect(isSupportedLocale("ru")).toBe(true);
    expect(isSupportedLocale("fr")).toBe(false);
    expect(isSupportedLocale("")).toBe(false);
    expect(isSupportedLocale(null)).toBe(false);
  });

  it("maps a code to its Intl tag and an unknown code to the default's", () => {
    expect(intlTag("ru")).toBe("ru");
    expect(intlTag("fr")).toBe(intlTag(DEFAULT_LOCALE));
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { initialLocale, reconcileLocale } from "./initialLocale";

function browserLanguage(language: string) {
  vi.spyOn(window.navigator, "language", "get").mockReturnValue(language);
}

beforeEach(() => browserLanguage("en-US"));
afterEach(() => vi.restoreAllMocks());

describe("initialLocale", () => {
  it("accepts a supported browser language and a stored locale", () => {
    browserLanguage("ru-RU");
    expect(initialLocale()).toBe("ru");

    window.localStorage.setItem("locale", "pl");
    expect(initialLocale()).toBe("pl");
  });

  it("ignores fr, in the browser and in storage, and falls back to de", () => {
    browserLanguage("fr-FR");
    expect(initialLocale()).toBe("de");

    window.localStorage.setItem("locale", "fr");
    expect(initialLocale()).toBe("de");
  });

  it("skips an unsupported stored value and reads the browser language next", () => {
    window.localStorage.setItem("locale", "fr");
    browserLanguage("uk-UA");

    expect(initialLocale()).toBe("uk");
  });
});

describe("reconcileLocale", () => {
  it("keeps a locale that is enabled", () => {
    expect(reconcileLocale("ru", ["de", "en", "ru"])).toBe("ru");
  });

  it("falls back to de for a locale that is not enabled", () => {
    expect(reconcileLocale("ru", ["de", "en"])).toBe("de");
  });

  it("keeps the locale while the enabled set is unknown or empty", () => {
    expect(reconcileLocale("ru", undefined)).toBe("ru");
    expect(reconcileLocale("ru", [])).toBe("ru");
  });
});

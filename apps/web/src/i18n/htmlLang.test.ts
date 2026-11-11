import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LOCALE_CODES } from "./localeMeta";

const INDEX_HTML = readFileSync(resolve(__dirname, "../../index.html"), "utf8");

/** Body of the one inline `<script>` in index.html (the one without `src`). */
function inlineScript(): string {
  const match = /<script>([\s\S]*?)<\/script>/.exec(INDEX_HTML);
  if (!match) throw new Error("index.html has no inline script");
  return match[1];
}

function runBeforeReact() {
  new Function(inlineScript())();
}

function browserLanguage(language: string) {
  vi.spyOn(window.navigator, "language", "get").mockReturnValue(language);
}

beforeEach(() => {
  document.documentElement.lang = "de";
  browserLanguage("en-US");
});
afterEach(() => vi.restoreAllMocks());

describe("index.html lang script", () => {
  it("ships the API default as the static lang", () => {
    expect(INDEX_HTML).toMatch(/<html lang="de">/);
  });

  it("sets lang from the stored locale before React mounts", () => {
    window.localStorage.setItem("locale", "ru");
    runBeforeReact();

    expect(document.documentElement.lang).toBe("ru");
  });

  it("falls back to the browser language when nothing is stored", () => {
    browserLanguage("pl-PL");
    runBeforeReact();

    expect(document.documentElement.lang).toBe("pl");
  });

  it("rejects an unsupported stored value and browser language", () => {
    window.localStorage.setItem("locale", "fr");
    browserLanguage("fr-FR");
    runBeforeReact();

    expect(document.documentElement.lang).toBe("de");
  });

  it("does not throw when storage is blocked and uses the browser language", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    browserLanguage("uk-UA");

    expect(runBeforeReact).not.toThrow();
    expect(document.documentElement.lang).toBe("uk");
  });

  it("lists the same locales as localeMeta", () => {
    const literal = /\[((?:"[a-z]{2}",?\s*)+)\]/.exec(inlineScript());

    expect(literal?.[1].match(/[a-z]{2}/g)).toEqual([...LOCALE_CODES]);
  });
});

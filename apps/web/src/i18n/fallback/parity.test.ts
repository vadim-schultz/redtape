import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { parityProblems, placeholders } from "../../test/localeParity";
import { flatten, type Nested } from "./index";

/** Every locale file next to this test, by code. */
function localeFiles(): Record<string, Record<string, string>> {
  return Object.fromEntries(
    readdirSync(__dirname)
      .filter((name) => name.endsWith(".json"))
      .map((name) => [
        name.replace(".json", ""),
        flatten(
          JSON.parse(readFileSync(resolve(__dirname, name), "utf8")) as Nested,
        ),
      ]),
  );
}

describe("parity", () => {
  it("locale files share key sets, placeholders and required plural forms", () => {
    const files = localeFiles();

    expect(Object.keys(files)).toContain("en");
    expect(parityProblems(files)).toEqual([]);
  });

  it("names the key and locale when a key is missing or extra", () => {
    const problems = parityProblems({
      en: { a: "A", b: "B" },
      ru: { a: "А", c: "С" },
    });

    expect(problems).toEqual(["ru: missing key b", "ru: extra key c"]);
  });

  it("names the key and locale when placeholders differ", () => {
    const problems = parityProblems({
      en: { greet: "Hi {name}" },
      ru: { greet: "Привет {user}" },
    });

    expect(problems).toEqual([
      "ru: greet has placeholders {user} but en has {name}",
    ]);
  });

  it("names the plural form a locale still needs", () => {
    const problems = parityProblems({
      en: { n_one: "{count} item", n_other: "{count} items" },
      ru: { n_one: "{count} штука", n_other: "{count} штук" },
    });

    expect(problems).toEqual([
      "ru: n lacks plural form few",
      "ru: n lacks plural form many",
    ]);
  });

  it("accepts a Russian family with all four forms against English's two", () => {
    const problems = parityProblems({
      en: { n_one: "{count} item", n_other: "{count} items" },
      ru: {
        n_one: "{count} штука",
        n_few: "{count} штуки",
        n_many: "{count} штук",
        n_other: "{count} штуки",
      },
    });

    expect(problems).toEqual([]);
  });

  it("does not treat a plain key that ends in _other as a plural form", () => {
    const bundle = { title: "Title", title_other: "Title (other language)" };

    expect(parityProblems({ en: bundle, de: bundle })).toEqual([]);
  });

  it("lists each placeholder once, sorted", () => {
    expect(placeholders("{b} and {a} and {b}")).toEqual(["a", "b"]);
  });
});

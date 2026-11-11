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

  it("removed sort keys are gone from every locale file", () => {
    const sortKeys = Object.entries(localeFiles()).flatMap(([locale, keys]) =>
      Object.keys(keys)
        .filter((key) => key.startsWith("documents.sort_"))
        .map((key) => `${locale}: ${key}`),
    );

    expect(sortKeys).toEqual([]);
  });

  it("fails the suite for a real locale file that loses a key or a placeholder", () => {
    const en = localeFiles().en;
    const [withPlaceholder] = Object.keys(en).filter((key) =>
      en[key].includes("{"),
    );
    const [dropped] = Object.keys(en).filter((key) => key !== withPlaceholder);
    const broken = {
      ...en,
      [withPlaceholder]: en[withPlaceholder].replace(/\{\w+\}/, ""),
    };
    delete broken[dropped];

    const problems = parityProblems({ en, xx: broken });

    expect(problems).toContain(`xx: missing key ${dropped}`);
    expect(problems.join("\n")).toContain(
      `xx: ${withPlaceholder} has placeholders`,
    );
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

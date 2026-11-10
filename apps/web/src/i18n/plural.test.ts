import { describe, expect, it } from "vitest";

import { pluralCategories, resolvePlural } from "./plural";
import { translate } from "./translate";

/** A family `item_<category>` that names its category, plus a plain `item`. */
function family(categories: readonly string[]): Record<string, string> {
  return Object.fromEntries(categories.map((c) => [`item_${c}`, `${c}`]));
}

const ALL = ["one", "few", "many", "other"] as const;

describe("t · picks plural forms per locale", () => {
  it.each([
    [
      "ru",
      ALL,
      [
        [1, "one"],
        [2, "few"],
        [5, "many"],
        [21, "one"],
        [1.5, "other"],
      ],
    ],
    [
      "pl",
      ALL,
      [
        [1, "one"],
        [3, "few"],
        [5, "many"],
        [22, "few"],
        [1.5, "other"],
      ],
    ],
    [
      "ro",
      ["one", "few", "other"],
      [
        [1, "one"],
        [2, "few"],
        [19, "few"],
        [20, "other"],
      ],
    ],
    [
      "tr",
      ["one", "other"],
      [
        [1, "one"],
        [2, "other"],
        [0, "other"],
      ],
    ],
    [
      "en",
      ["one", "other"],
      [
        [1, "one"],
        [2, "other"],
        [0, "other"],
      ],
    ],
  ] as const)("%s", (tag, categories, cases) => {
    const bundle = family(categories);

    for (const [count, expected] of cases) {
      expect(translate(bundle, tag, "item", { count }), `${count}`).toBe(
        expected,
      );
    }
  });

  it("interpolates the count and other params into the chosen form", () => {
    const bundle = {
      item_one: "{count} Dokument in {where}",
      item_other: "{count} Dokumente in {where}",
    };

    expect(translate(bundle, "de", "item", { count: 3, where: "Bern" })).toBe(
      "3 Dokumente in Bern",
    );
  });

  it("reads the categories a locale needs from Intl, not from a list", () => {
    expect([...pluralCategories("ru")].sort()).toEqual([
      "few",
      "many",
      "one",
      "other",
    ]);
    expect([...pluralCategories("ro")].sort()).toEqual(["few", "one", "other"]);
    expect([...pluralCategories("tr")].sort()).toEqual(["one", "other"]);
  });
});

describe("t · a missing plural form", () => {
  it("falls back to _other, then to the plain key, and never throws", () => {
    expect(
      translate({ item_other: "other form" }, "ru", "item", { count: 1 }),
    ).toBe("other form");
    expect(translate({ item: "plain" }, "ru", "item", { count: 1 })).toBe(
      "plain",
    );
    expect(translate({}, "ru", "item", { count: 1 })).toBe("item");
  });

  it("ignores a count that is not a number and reads the plain key", () => {
    expect(
      translate({ item: "plain", item_other: "other" }, "en", "item", {
        count: "x",
      }),
    ).toBe("plain");
    expect(resolvePlural({ item_other: "o" }, "item", Number.NaN, "en")).toBe(
      "o",
    );
  });

  it("without a count, reads the plain key even when plural forms exist", () => {
    expect(
      translate({ item: "plain", item_other: "other" }, "en", "item"),
    ).toBe("plain");
  });
});

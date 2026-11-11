import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { FONT_STACKS } from "./fonts";

const FONTS_SOURCE = readFileSync(resolve(__dirname, "fonts.ts"), "utf8");
const FONTSOURCE = resolve(__dirname, "../../node_modules/@fontsource");

/** Letters the Latin-ext subset must carry for Turkish, Polish and Romanian. */
const LATIN_EXT = {
  tr: "ğşİıÇçÖöÜü",
  pl: "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
  ro: "ăâîșțĂÂÎȘȚ",
};
/** Letters Russian and Ukrainian headings need, including ї є і ґ. */
const CYRILLIC =
  "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюяЇїЄєІіҐґ";

/** `[family, weight]` for every `@fontsource/<family>/<weight>.css` import in fonts.ts. */
function importedFaces(source: string): [string, string][] {
  return [...source.matchAll(/@fontsource\/([\w-]+)\/(\d+)\.css/g)].map((m) => [
    m[1],
    m[2],
  ]);
}

/** Code point ranges declared by every `unicode-range` in a Fontsource stylesheet. */
function rangesOf(css: string): [number, number][] {
  return [...css.matchAll(/unicode-range:([^;]+);/g)]
    .flatMap((m) => m[1].split(","))
    .map((part) => part.trim().replace("U+", "").split("-"))
    .map(([lo, hi]) => [parseInt(lo, 16), parseInt(hi ?? lo, 16)]);
}

/** Characters of `text` that no range in `css` covers. */
export function uncovered(css: string, text: string): string[] {
  const ranges = rangesOf(css);
  return [...text].filter((ch) => {
    const point = ch.codePointAt(0) as number;
    return !ranges.some(([lo, hi]) => point >= lo && point <= hi);
  });
}

function stylesheet(family: string, weight: string): string {
  return readFileSync(resolve(FONTSOURCE, family, `${weight}.css`), "utf8");
}

describe("fonts · Latin-ext for Turkish, Polish and Romanian", () => {
  it.each(importedFaces(FONTS_SOURCE))(
    "%s %s delivers the subset",
    (family, weight) => {
      const css = stylesheet(family, weight);

      for (const [locale, letters] of Object.entries(LATIN_EXT)) {
        expect(
          uncovered(css, letters),
          `${family} ${weight} ${locale}`,
        ).toEqual([]);
      }
    },
  );

  it("reports the characters a stylesheet does not cover", () => {
    const latinOnly = "@font-face { unicode-range: U+0000-00FF, U+0131; }";

    expect(uncovered(latinOnly, "ğaı")).toEqual(["ğ"]);
  });
});

describe("fonts · Cyrillic headings", () => {
  it("Space Grotesk alone has no Cyrillic, which is why the stack needs a fallback", () => {
    expect(uncovered(stylesheet("space-grotesk", "600"), CYRILLIC)).not.toEqual(
      [],
    );
  });

  it("Inter, loaded in every body weight, covers Russian and Ukrainian letters", () => {
    for (const [family, weight] of importedFaces(FONTS_SOURCE)) {
      if (family === "inter") {
        expect(uncovered(stylesheet(family, weight), CYRILLIC), weight).toEqual(
          [],
        );
      }
    }
  });

  it("the heading stack names Space Grotesk first and Inter before the system font", () => {
    const names = FONT_STACKS.heading.split(",").map((name) => name.trim());

    expect(names.indexOf("'Space Grotesk'")).toBe(0);
    expect(names.indexOf("'Inter'")).toBeGreaterThan(0);
    expect(names.indexOf("'Inter'")).toBeLessThan(names.indexOf("system-ui"));
  });
});

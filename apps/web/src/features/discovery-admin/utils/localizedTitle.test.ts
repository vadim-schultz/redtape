import { describe, expect, it } from "vitest";

import { localizedTitle } from "./localizedTitle";

describe("localizedTitle", () => {
  it("returns the title in the requested locale", () => {
    expect(localizedTitle({ de: "Titel", en: "Title" }, "de")).toBe("Titel");
  });

  it.each([
    ["en", { en: "Title", de: "Titel", fr: "Titre" }, "Title"],
    ["fr", { de: "Titel", ja: "題名" }, "Titel"],
    ["fr", { fr: "Titre", ja: "題名" }, "Titre"],
    ["fr", { ja: "題名", xx: "x" }, "題名"],
  ])(
    "locale %s falls back through en, de, then any key",
    (locale, title, expected) => {
      expect(localizedTitle(title, locale)).toBe(expected);
    },
  );

  it("returns an empty string for an empty object", () => {
    expect(localizedTitle({}, "de")).toBe("");
  });

  it("returns an empty requested-locale value as is, without falling through", () => {
    expect(localizedTitle({ de: "", en: "Title" }, "de")).toBe("");
  });
});

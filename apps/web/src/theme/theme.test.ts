import { expect, it } from "vitest";

import { system } from "./index";

const UNREGISTERED_SEMANTIC_TOKEN = "colors.not.a.real.token";

function semanticBase(path: string): unknown {
  const token = system.tokens.getByName(path);
  const conditions = token?.extensions.conditions;
  if (!conditions || typeof conditions !== "object") {
    return undefined;
  }
  return conditions.base;
}

function modeValue(path: string, key: "base" | "_dark"): string {
  const conditions = system.tokens.getByName(path)?.extensions.conditions as
    Record<string, string> | undefined;
  const ref = conditions?.[key] ?? "";
  const match = /^\{(.+)\}$/.exec(ref);
  return match ? (system.token(match[1]) as string) : ref;
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map(
    (i) => parseInt(hex.slice(i, i + 2), 16) / 255,
  );
  const [r, g, b] = channels.map((c) =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

it("theme · primary.500 is Swiss red #DA291C", () => {
  expect(system.token("colors.primary.500")).toBe("#DA291C");
});

it("theme · text.heading is the same Swiss red in light and dark mode", () => {
  const heading = semanticBase("colors.text.heading") as string | undefined;
  const headingDark = system.tokens.getByName("colors.text.heading")?.extensions
    .conditions as { _dark?: string } | undefined;

  expect(heading).toBe("{colors.primary.500}");
  expect(headingDark?._dark).toBe("{colors.primary.500}");
});

it("theme · accent.500 is #EE4C7C", () => {
  expect(system.token("colors.accent.500")).toBe("#EE4C7C");
});

it("theme · light bg.canvas is #E3E2DF", () => {
  expect(semanticBase("colors.bg.canvas")).toBe("#E3E2DF");
});

it("theme · heading font token names Space Grotesk", () => {
  expect(system.token("fonts.heading")).toContain("Space Grotesk");
});

it("theme · no appTitle text style or brand font token", () => {
  const styles = system._config.theme?.textStyles ?? {};

  expect(styles).not.toHaveProperty("appTitle");
  expect(system.token("fonts.brand")).toBeUndefined();
});

it("theme · brand.mark resolves to Swiss red in light mode", () => {
  expect(modeValue("colors.brand.mark", "base")).toBe("#DA291C");
});

it("theme · brand.mark meets 3:1 contrast on nav.bg in light and dark", () => {
  const cases = [
    ["base", "#FFFFFF"],
    ["_dark", system.token("colors.gray.900") as string],
  ] as const;

  for (const [key, bg] of cases) {
    const fg = modeValue("colors.brand.mark", key);
    expect(contrast(fg, bg), key).toBeGreaterThanOrEqual(3);
  }
});

it("theme · body font token names Inter", () => {
  expect(system.token("fonts.body")).toContain("Inter");
});

it("theme · pageTitle text style is bold", () => {
  const pageTitle = system._config.theme?.textStyles?.pageTitle?.value as
    { fontWeight?: string } | undefined;

  expect(pageTitle?.fontWeight).toBe("bold");
});

it("theme · focus.ring semantic is defined", () => {
  expect(system.token("colors.focus.ring")).toBeTruthy();
});

it("theme · rejects unregistered semantic token lookup", () => {
  expect(system.tokens.getByName(UNREGISTERED_SEMANTIC_TOKEN)).toBeUndefined();
  expect(system.token(UNREGISTERED_SEMANTIC_TOKEN)).toBeUndefined();
});

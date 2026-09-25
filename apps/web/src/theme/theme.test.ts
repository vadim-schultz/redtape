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

it("theme · brand font token names Iceberg", () => {
  expect(system.token("fonts.brand")).toContain("Iceberg");
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

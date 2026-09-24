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

it("theme · primary.500 is wine #9A1750", () => {
  expect(system.token("colors.primary.500")).toBe("#9A1750");
});

it("theme · accent.500 is #EE4C7C", () => {
  expect(system.token("colors.accent.500")).toBe("#EE4C7C");
});

it("theme · light bg.canvas is #E3E2DF", () => {
  expect(semanticBase("colors.bg.canvas")).toBe("#E3E2DF");
});

it("theme · heading font token names Iceberg", () => {
  expect(system.token("fonts.heading")).toContain("Iceberg");
});

it("theme · body font token names Inter", () => {
  expect(system.token("fonts.body")).toContain("Inter");
});

it("theme · pageTitle text style is bold", () => {
  const pageTitle = system._config.theme?.textStyles?.pageTitle?.value as
    { fontWeight?: string } | undefined;

  expect(pageTitle?.fontWeight).toBe("bold");
});

it("theme · rejects unregistered semantic token lookup", () => {
  expect(system.tokens.getByName(UNREGISTERED_SEMANTIC_TOKEN)).toBeUndefined();
  expect(system.token(UNREGISTERED_SEMANTIC_TOKEN)).toBeUndefined();
});

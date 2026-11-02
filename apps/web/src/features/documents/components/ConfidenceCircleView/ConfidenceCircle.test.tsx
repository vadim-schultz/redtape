import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import ConfidenceCircle from "./ConfidenceCircle";

async function renderCircle(confidence: number) {
  renderWithProviders(<ConfidenceCircle confidence={confidence} />);
  return screen.findByRole("progressbar");
}

function cssRules(): string[] {
  return [...document.styleSheets].flatMap((sheet) =>
    [...sheet.cssRules].map((rule) => rule.cssText),
  );
}

function rulesOf(el: Element): string {
  const cls = [...el.classList].find((name) => name.startsWith("css-"));
  return cssRules()
    .filter((rule) => rule.includes(`.${cls} `))
    .join("\n");
}

describe("ConfidenceCircle palette", () => {
  it.each([
    [0.2, "red"],
    [0.55, "yellow"],
    [0.9, "green"],
  ])("confidence %s paints the whole ring in %s", async (value, hue) => {
    const bar = await renderCircle(value);
    const [track, range] = bar.querySelectorAll("circle");

    expect(rulesOf(bar.parentElement!)).toContain(
      `--chakra-colors-color-palette-solid: var(--chakra-colors-${hue}-solid)`,
    );
    expect(rulesOf(track)).toContain(
      "var(--chakra-colors-color-palette-muted)",
    );
    expect(rulesOf(range)).toContain(
      "var(--chakra-colors-color-palette-solid)",
    );
  });
});

describe("ConfidenceCircle value", () => {
  it("shows the percentage and exposes it as aria-valuenow", async () => {
    const bar = await renderCircle(0.456);

    expect(bar).toHaveAttribute("aria-valuenow", "46");
    expect(bar.parentElement).toHaveTextContent("46%");
  });

  it("labels the circle with the percentage and the band", async () => {
    const bar = await renderCircle(0.75);

    expect(bar).toHaveAccessibleName("Confidence 75%, high");
  });

  it.each([
    [Number.NaN, "0", "Confidence 0%, low"],
    [-0.2, "0", "Confidence 0%, low"],
    [Number.POSITIVE_INFINITY, "0", "Confidence 0%, low"],
    [1.7, "100", "Confidence 100%, high"],
  ])("renders %s clamped without throwing", async (value, now, label) => {
    const bar = await renderCircle(value);

    expect(bar).toHaveAttribute("aria-valuenow", now);
    expect(bar).toHaveAccessibleName(label);
  });

  it("is neither a link nor a button", async () => {
    await renderCircle(0.5);

    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });
});

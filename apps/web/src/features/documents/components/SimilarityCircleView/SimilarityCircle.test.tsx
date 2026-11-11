import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { emotionRules } from "../../../../test/emotionRules";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import SimilarityCircle from "./SimilarityCircle";

async function renderCircle(similarity: number) {
  renderWithProviders(<SimilarityCircle similarity={similarity} />);
  return screen.findByRole("progressbar");
}

describe("SimilarityCircle", () => {
  it.each([
    [0.2, "red", "low"],
    [0.55, "yellow", "medium"],
    [0.9, "green", "high"],
  ])(
    "uses the band colours and the similarity aria label (%s)",
    async (value, hue, band) => {
      const bar = await renderCircle(value);

      expect(emotionRules(bar.parentElement!)).toContain(
        `--chakra-colors-color-palette-solid: var(--chakra-colors-${hue}-solid)`,
      );
      expect(bar).toHaveAccessibleName(
        `Similarity ${Math.round(value * 100)}%, ${band}`,
      );
      expect(bar).toHaveAttribute(
        "aria-valuenow",
        String(Math.round(value * 100)),
      );
    },
  );

  it.each([
    [Number.NaN, "0", "Similarity 0%, low"],
    [-0.2, "0", "Similarity 0%, low"],
    [Number.POSITIVE_INFINITY, "0", "Similarity 0%, low"],
    [1.7, "100", "Similarity 100%, high"],
  ])(
    "clamps %s outside 0..1 and non-finite values",
    async (value, now, label) => {
      const bar = await renderCircle(value);

      expect(bar).toHaveAttribute("aria-valuenow", now);
      expect(bar).toHaveAccessibleName(label);
    },
  );
});

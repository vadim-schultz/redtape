import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { emotionRules } from "../../test/emotionRules";
import { renderWithProviders } from "../../test/renderWithProviders";
import ScoreRing from "./ScoreRing";

describe("ScoreRing", () => {
  it("renders value, palette and label", async () => {
    renderWithProviders(<ScoreRing value={64} palette="yellow" label="Fit" />);

    const bar = await screen.findByRole("progressbar");
    const [track, range] = bar.querySelectorAll("circle");

    expect(bar).toHaveAttribute("aria-valuenow", "64");
    expect(bar).toHaveAccessibleName("Fit");
    expect(bar.parentElement).toHaveTextContent("64%");
    expect(emotionRules(bar.parentElement!)).toContain(
      "--chakra-colors-color-palette-solid: var(--chakra-colors-yellow-solid)",
    );
    expect(emotionRules(track)).toContain(
      "var(--chakra-colors-color-palette-muted)",
    );
    expect(emotionRules(range)).toContain(
      "var(--chakra-colors-color-palette-solid)",
    );
  });

  it("is not interactive and carries the label as its tooltip title", async () => {
    renderWithProviders(<ScoreRing value={10} palette="red" label="Fit" />);

    const bar = await screen.findByRole("progressbar");

    expect(bar.closest("[title]")).toHaveAttribute("title", "Fit");
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });
});

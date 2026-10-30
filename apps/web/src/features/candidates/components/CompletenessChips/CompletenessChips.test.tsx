import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import { ALL_FLAGS } from "../../../../test/candidateFixtures";
import CompletenessChips from "./CompletenessChips";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("completeness chips announce present and missing flags", () => {
  renderWithProviders(
    <CompletenessChips flags={{ ...ALL_FLAGS, has_screenshot: false }} />,
  );

  expect(
    screen.getByRole("listitem", { name: "Screenshot: missing" }),
  ).toBeInTheDocument();
  expect(screen.getAllByRole("listitem", { name: /: present$/ })).toHaveLength(
    4,
  );
});

it("completeness chips show five present chips for a complete candidate", () => {
  renderWithProviders(<CompletenessChips flags={ALL_FLAGS} />);

  const chips = screen.getAllByRole("listitem");
  expect(chips).toHaveLength(5);
  chips.forEach((chip) => expect(chip).toHaveAccessibleName(/: present$/));
  expect(screen.queryByRole("listitem", { name: /missing/ })).toBeNull();
});

it("completeness chips keep a visible text label on every chip", () => {
  renderWithProviders(
    <CompletenessChips flags={{ ...ALL_FLAGS, has_edges: false }} />,
  );

  const labels = [
    "Domain",
    "Situation",
    "Dependencies",
    "Snapshot",
    "Screenshot",
  ];
  const chips = screen.getAllByRole("listitem");
  labels.forEach((label, index) =>
    expect(within(chips[index]).getByText(label)).toBeVisible(),
  );
});

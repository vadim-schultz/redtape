import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { ALL_FLAGS } from "../../../test/candidateFixtures";
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
    3,
  );
});

it("completeness chips show four present chips for a complete candidate", () => {
  renderWithProviders(<CompletenessChips flags={ALL_FLAGS} />);

  const chips = screen.getAllByRole("listitem");
  expect(chips).toHaveLength(4);
  chips.forEach((chip) => expect(chip).toHaveAccessibleName(/: present$/));
  expect(screen.queryByRole("listitem", { name: /missing/ })).toBeNull();
});

it("completeness chips keep a visible text label on every chip", () => {
  renderWithProviders(
    <CompletenessChips flags={{ ...ALL_FLAGS, has_edges: false }} />,
  );

  const labels = ["Category", "Dependencies", "Snapshot", "Screenshot"];
  const chips = screen.getAllByRole("listitem");
  labels.forEach((label, index) =>
    expect(within(chips[index]).getByText(label)).toBeVisible(),
  );
});

it("completeness chips stack in a column in the vertical variant", () => {
  renderWithProviders(
    <CompletenessChips flags={ALL_FLAGS} orientation="vertical" />,
  );

  const list = screen.getAllByRole("listitem")[0].parentElement!;
  expect(getComputedStyle(list).flexDirection).toBe("column");
});

it("completeness chips keep a row by default", () => {
  renderWithProviders(<CompletenessChips flags={ALL_FLAGS} />);

  const list = screen.getAllByRole("listitem")[0].parentElement!;
  expect(getComputedStyle(list).flexDirection).toBe("row");
});

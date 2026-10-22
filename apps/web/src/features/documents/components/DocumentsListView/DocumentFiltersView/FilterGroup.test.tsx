import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../../test/renderWithProviders";
import FilterGroup from "./FilterGroup";

const terms = [
  { code: "housing", name: "Housing", description: "", icon: null },
  { code: "work", name: "Work", description: "", icon: null },
];

it("FilterGroup · renders a heading and one chip per term with selection", () => {
  renderWithProviders(
    <FilterGroup
      heading="Domain"
      terms={terms}
      selected={["work"]}
      onToggle={vi.fn()}
    />,
  );

  expect(screen.getByText("Domain")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Housing" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  expect(screen.getByRole("button", { name: "Work" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

it("FilterGroup · toggling a chip reports its code", async () => {
  const onToggle = vi.fn();
  const { user } = renderWithProviders(
    <FilterGroup
      heading="Domain"
      terms={terms}
      selected={[]}
      onToggle={onToggle}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Housing" }));

  expect(onToggle).toHaveBeenCalledWith("housing");
});

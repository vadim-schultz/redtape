import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../../test/renderWithProviders";
import FilterChip from "./FilterChip";

it("FilterChip · reports pressed state via aria-pressed", () => {
  renderWithProviders(
    <FilterChip label="Housing" pressed onToggle={vi.fn()} />,
  );

  expect(screen.getByRole("button", { name: "Housing" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

it("FilterChip · unpressed chip reports aria-pressed false", () => {
  renderWithProviders(
    <FilterChip label="Housing" pressed={false} onToggle={vi.fn()} />,
  );

  expect(screen.getByRole("button", { name: "Housing" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});

it("FilterChip · click calls onToggle", async () => {
  const onToggle = vi.fn();
  const { user } = renderWithProviders(
    <FilterChip label="Housing" pressed={false} onToggle={onToggle} />,
  );

  await user.click(screen.getByRole("button", { name: "Housing" }));

  expect(onToggle).toHaveBeenCalledOnce();
});

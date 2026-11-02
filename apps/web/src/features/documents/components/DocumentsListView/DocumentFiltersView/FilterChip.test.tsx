import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { elementCss } from "../../../../../test/elementCss";
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

function chipCss(
  tone: "plain" | "group" | "sub",
  pressed: boolean,
  partial = false,
): string {
  const { unmount } = renderWithProviders(
    <FilterChip
      label="Chip"
      tone={tone}
      pressed={pressed}
      partial={partial}
      onToggle={vi.fn()}
    />,
  );
  const css = elementCss(screen.getByRole("button", { name: "Chip" }));
  unmount();
  return css;
}

it("FilterChip · a pressed group chip is styled exactly like a pressed plain chip", () => {
  const plain = chipCss("plain", true);

  expect(plain).not.toBe("");
  expect(chipCss("group", true)).toBe(plain);
});

it("FilterChip · a pressed sub chip asks for the lighter chip tokens, not primary solid", () => {
  const css = chipCss("sub", true);

  expect(css).toContain("--chakra-colors-chip-sub-selected-bg");
  expect(css).not.toBe(chipCss("plain", true));
});

it("FilterChip · a group chip with sub-selections is outlined, a bare one is subtle", () => {
  const bare = chipCss("group", false);

  expect(bare).not.toBe("");
  expect(bare).toBe(chipCss("plain", false));
  expect(chipCss("group", false, true)).not.toBe(bare);
});

it("FilterChip · an unpressed sub chip keeps the plain unpressed look", () => {
  expect(chipCss("sub", false)).toBe(chipCss("plain", false));
});

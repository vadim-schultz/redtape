import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";

import KeyValueRow from "./KeyValueRow";

function renderRow() {
  return renderWithProviders(
    <KeyValueRow label="Label">
      <span>Value</span>
    </KeyValueRow>,
  );
}

function gridRoot(container: HTMLElement) {
  const grid = container.querySelector('[data-testid="key-value-row"]');
  expect(grid).toBeTruthy();
  return grid as HTMLElement;
}

it("KeyValueRow · uses a 1fr / 3fr column template", () => {
  const { container } = renderRow();

  const columns = getComputedStyle(gridRoot(container)).gridTemplateColumns;

  expect(columns).toMatch(/1fr/);
  expect(columns).toMatch(/3fr/);
});

it("KeyValueRow · vertically centres label and value", () => {
  const { container } = renderRow();

  expect(getComputedStyle(gridRoot(container)).alignItems).toBe("center");
});

it("KeyValueRow · renders the label text", () => {
  renderRow();

  expect(screen.getByText("Label")).toBeInTheDocument();
  expect(screen.getByText("Value")).toBeInTheDocument();
});

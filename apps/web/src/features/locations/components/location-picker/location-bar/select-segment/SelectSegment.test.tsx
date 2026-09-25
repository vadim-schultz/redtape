import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../../../test/renderWithProviders";
import SelectSegment, { type SelectSegmentProps } from "./SelectSegment";

function renderSegment(props: Partial<SelectSegmentProps> = {}) {
  return renderWithProviders(
    <SelectSegment
      label="State"
      value=""
      disabled={false}
      options={[{ code: "BE", name: "Berlin", kind: "REGION" }]}
      onChange={vi.fn()}
      isLoading={false}
      {...props}
    />,
  );
}

it("SelectSegment · shows its label as the placeholder and accessible name", () => {
  renderSegment();

  expect(screen.getByRole("combobox", { name: "State" })).toBeInTheDocument();
  expect(screen.getByText("State")).toBeInTheDocument();
});

it("SelectSegment · reports the chosen code", async () => {
  const onChange = vi.fn();
  const { user } = renderSegment({ onChange });

  await user.click(screen.getByRole("combobox"));
  await user.click(await screen.findByRole("option", { name: "Berlin" }));

  expect(onChange).toHaveBeenCalledWith("BE");
});

it("SelectSegment · shows the chosen option name", () => {
  renderSegment({ value: "BE" });

  expect(screen.getByRole("combobox")).toHaveTextContent("Berlin");
});

it("SelectSegment · disabled segment is disabled and does not lift on hover", () => {
  renderSegment({ disabled: true });

  const trigger = screen.getByRole("combobox");

  expect(trigger).toBeDisabled();
  expect(getComputedStyle(trigger).transform).not.toContain("translateY");
});

it("SelectSegment · flags itself busy while loading", () => {
  renderSegment({ isLoading: true });

  expect(screen.getByRole("combobox")).toHaveAttribute("aria-busy", "true");
});

it("SelectSegment · is not busy when loaded", () => {
  renderSegment();

  expect(screen.getByRole("combobox")).not.toHaveAttribute("aria-busy", "true");
});

import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../../../test/renderWithProviders";
import LeafFacet from "./LeafFacet";

it("LeafFacet · renders nothing when there are no codes", () => {
  const { container } = renderWithProviders(
    <LeafFacet codes={[]} selected={[]} onToggle={vi.fn()} />,
  );

  expect(container.querySelector("button")).toBeNull();
});

it("LeafFacet · renders one chip per code", () => {
  renderWithProviders(
    <LeafFacet
      codes={["1050200", "1050300"]}
      selected={[]}
      onToggle={vi.fn()}
    />,
  );

  expect(screen.getByRole("button", { name: "1050200" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "1050300" })).toBeInTheDocument();
});

it("LeafFacet · marks a selected code as pressed", () => {
  renderWithProviders(
    <LeafFacet codes={["1050200"]} selected={["1050200"]} onToggle={vi.fn()} />,
  );

  expect(screen.getByRole("button", { name: "1050200" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

it("LeafFacet · clicking a chip reports its code", async () => {
  const onToggle = vi.fn();
  const { user } = renderWithProviders(
    <LeafFacet codes={["1050200"]} selected={[]} onToggle={onToggle} />,
  );

  await user.click(screen.getByRole("button", { name: "1050200" }));

  expect(onToggle).toHaveBeenCalledWith("1050200");
});

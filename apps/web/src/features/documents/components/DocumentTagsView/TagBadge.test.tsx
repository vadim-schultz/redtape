import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import TagBadge from "./TagBadge";

function opacity(name: string): string {
  return screen.getByText(name).closest("a")!.style.opacity;
}

it("TagBadge · confidence 1.0 renders fully opaque, matching today's rendering", () => {
  renderWithProviders(
    <TagBadge to="/documents?domain=housing" name="Housing" confidence={1.0} />,
  );

  expect(opacity("Housing")).toBe("1");
});

it("TagBadge · a lower confidence renders a lower opacity, never fully transparent", () => {
  renderWithProviders(
    <TagBadge to="/documents?domain=housing" name="Housing" confidence={0} />,
  );

  expect(opacity("Housing")).toBe("0.5");
});

it("TagBadge · opacity scales linearly with confidence", () => {
  renderWithProviders(
    <TagBadge to="/documents?domain=housing" name="Housing" confidence={0.4} />,
  );

  expect(opacity("Housing")).toBe("0.7");
});

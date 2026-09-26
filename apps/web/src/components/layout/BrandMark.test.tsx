import { render } from "@testing-library/react";
import { expect, it } from "vitest";

import BrandMark from "./BrandMark";

it("BrandMark · fills with currentColor and has no background rect", () => {
  const { container } = render(<BrandMark />);
  const svg = container.querySelector("svg");

  expect(svg?.querySelector("rect")).toBeNull();
  expect(svg?.querySelector("path")).toHaveAttribute("fill", "currentColor");
  expect(container.innerHTML).not.toContain("#1f3a5f");
});

it("BrandMark · is hidden from assistive tech", () => {
  const { container } = render(<BrandMark />);

  expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
});

it("BrandMark · viewBox is cropped to the glyph, not the source canvas", () => {
  const { container } = render(<BrandMark />);
  const [x, y, w, h] = container
    .querySelector("svg")!
    .getAttribute("viewBox")!
    .split(" ")
    .map(Number);

  expect(x).toBeGreaterThan(10);
  expect(y).toBeGreaterThan(8);
  expect(w).toBeLessThan(42);
  expect(h).toBeLessThan(46);
  expect(x + w).toBeGreaterThan(49.75);
  expect(y + h).toBeGreaterThan(53.1);
});

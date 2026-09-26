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

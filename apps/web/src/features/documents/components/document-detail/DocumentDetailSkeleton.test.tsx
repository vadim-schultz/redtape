import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import DocumentDetailSkeleton from "./DocumentDetailSkeleton";

it("DocumentDetailSkeleton · announces loading and outlines title, description and requirements", () => {
  window.localStorage.setItem("locale", "en");
  const { container } = renderWithProviders(<DocumentDetailSkeleton />);

  const region = screen.getByRole("status", { name: "Loading..." });
  expect(region).toHaveAttribute("aria-busy", "true");
  expect(container.querySelectorAll(".chakra-skeleton").length).toBeGreaterThanOrEqual(8);
});

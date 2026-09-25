import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import DocumentsListSkeleton from "./DocumentsListSkeleton";

it("DocumentsListSkeleton · announces loading and mimics a list of cards", () => {
  window.localStorage.setItem("locale", "en");
  const { container } = renderWithProviders(<DocumentsListSkeleton />);

  const region = screen.getByRole("status", { name: "Loading..." });
  expect(region).toHaveAttribute("aria-busy", "true");
  expect(container.querySelectorAll(".chakra-card__root")).toHaveLength(4);
  expect(container.querySelectorAll(".chakra-skeleton").length).toBeGreaterThan(
    4,
  );
});

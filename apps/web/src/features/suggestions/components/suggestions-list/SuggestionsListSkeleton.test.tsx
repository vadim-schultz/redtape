import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import SuggestionsListSkeleton from "./SuggestionsListSkeleton";

it("SuggestionsListSkeleton · announces loading and mimics a list of cards", () => {
  window.localStorage.setItem("locale", "en");
  const { container } = renderWithProviders(<SuggestionsListSkeleton />);

  const region = screen.getByRole("status", { name: "Loading..." });
  expect(region).toHaveAttribute("aria-busy", "true");
  expect(container.querySelectorAll(".chakra-card__root")).toHaveLength(4);
  expect(container.querySelectorAll(".chakra-skeleton").length).toBeGreaterThan(
    4,
  );
});

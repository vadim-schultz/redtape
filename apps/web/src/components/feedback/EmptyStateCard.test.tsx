import { screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { LuFileSearch } from "react-icons/lu";

import { renderWithProviders } from "../../test/renderWithProviders";
import EmptyStateCard from "./EmptyStateCard";

it("EmptyStateCard · renders title, description and action", () => {
  renderWithProviders(
    <EmptyStateCard
      icon={LuFileSearch}
      title="Nothing here"
      description="Try another place"
      action={<button type="button">Change</button>}
    />,
  );

  expect(
    screen.getByRole("heading", { name: "Nothing here" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Try another place")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Change" })).toBeInTheDocument();
});

it("EmptyStateCard · icon is decorative", () => {
  const { container } = renderWithProviders(
    <EmptyStateCard icon={LuFileSearch} title="Nothing here" />,
  );

  expect(
    container.querySelector("svg")?.closest("[aria-hidden]"),
  ).toHaveAttribute("aria-hidden", "true");
});

it("EmptyStateCard · omits description and action when not given", () => {
  renderWithProviders(<EmptyStateCard icon={LuFileSearch} title="Nothing" />);

  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(screen.getByRole("status").textContent).toBe("Nothing");
});

it("EmptyStateCard · error variant tints the icon as an error", () => {
  const { container } = renderWithProviders(
    <EmptyStateCard icon={LuFileSearch} title="Oops" variant="error" />,
  );

  const indicator = container.querySelector(".chakra-empty-state__indicator");
  expect(getComputedStyle(indicator as Element).color).toBe(
    "var(--chakra-colors-status-error-text)",
  );
});

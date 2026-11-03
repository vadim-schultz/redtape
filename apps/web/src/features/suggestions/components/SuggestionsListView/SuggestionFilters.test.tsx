import { screen } from "@testing-library/react";
import { useLocation } from "react-router-dom";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import SuggestionFilters from "./SuggestionFilters";

function LocationProbe() {
  return <output data-testid="search">{useLocation().search}</output>;
}

function renderFilters(url = "/suggestions") {
  return renderWithProviders(
    <>
      <SuggestionFilters />
      <LocationProbe />
    </>,
    { initialEntries: [url] },
  );
}

it("SuggestionFilters · Pending is pressed by default", () => {
  renderFilters();

  expect(screen.getByRole("button", { name: "Pending" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

it("SuggestionFilters · clicking Approved writes status=approved to the URL", async () => {
  const { user } = renderFilters();

  await user.click(screen.getByRole("button", { name: "Approved" }));

  expect(screen.getByTestId("search")).toHaveTextContent("?status=approved");
  expect(screen.getByRole("button", { name: "Approved" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(screen.getByRole("button", { name: "Pending" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});

it("SuggestionFilters · clicking Pending after Approved clears the status param", async () => {
  const { user } = renderFilters("/suggestions?status=approved");

  await user.click(screen.getByRole("button", { name: "Pending" }));

  expect(screen.getByTestId("search")).toHaveTextContent("");
});

it("SuggestionFilters · renders one chip per status filter in order", () => {
  renderFilters();

  const chips = screen.getAllByRole("button");

  expect(chips.map((chip) => chip.textContent)).toEqual([
    "Pending",
    "All",
    "Approved",
    "Rejected",
  ]);
});

it("SuggestionFilters · reads All from the URL", () => {
  renderFilters("/suggestions?status=all");

  expect(screen.getByRole("button", { name: "All" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

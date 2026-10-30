import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { neighbourFixture } from "../../../../test/candidateFixtures";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import NeighbourCard from "./NeighbourCard";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("neighbour card falls back to the excerpt without a description", () => {
  renderWithProviders(
    <NeighbourCard neighbour={neighbourFixture({ description: null })} />,
  );

  expect(
    screen.getByText("Please bring your birth certificate."),
  ).toBeInTheDocument();
});

it("neighbour card shows the description instead of the excerpt", () => {
  renderWithProviders(<NeighbourCard neighbour={neighbourFixture()} />);

  expect(
    screen.getByText("Issued by the registry office."),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Please bring/)).toBeNull();
});

it("neighbour card links to the neighbour's own page", () => {
  renderWithProviders(<NeighbourCard neighbour={neighbourFixture()} />);

  expect(screen.getByRole("link")).toHaveAttribute("href", "/candidates/n1");
});

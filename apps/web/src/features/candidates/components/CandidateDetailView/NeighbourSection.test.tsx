import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { neighbourFixture } from "../../../../test/candidateFixtures";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import NeighbourSection from "./NeighbourSection";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const ingress = [
  neighbourFixture({
    id: "n1",
    title: "Birth certificate",
    condition: "if born abroad",
  }),
  neighbourFixture({ id: "n2", title: "Photo", is_optional: true }),
];

it("the ingress content keeps neighbour links and metadata", () => {
  renderWithProviders(
    <NeighbourSection items={ingress} emptyText="No documents staged" />,
  );

  const links = screen.getAllByRole("link");
  expect(links.map((link) => link.getAttribute("href"))).toEqual([
    "/candidates/n1",
    "/candidates/n2",
  ]);
  expect(within(links[0]).getByText("Condition: if born abroad")).toBeVisible();
  expect(within(links[1]).getByText("Optional")).toBeVisible();
  expect(within(links[0]).queryByText("Optional")).toBeNull();
  expect(screen.queryByText("Ingress")).toBeNull();
});

it("the egress heading reads the plain-language text", () => {
  renderWithProviders(
    <>
      <NeighbourSection items={ingress} emptyText="No documents staged" />
      <NeighbourSection
        items={[neighbourFixture({ id: "e1", title: "Residence permit" })]}
        emptyText="No documents staged"
      />
    </>,
  );

  expect(screen.getByText("Residence permit")).toBeVisible();
  expect(screen.getByText("Birth certificate")).toBeVisible();
});

it("the section renders content without an extra heading", () => {
  renderWithProviders(
    <NeighbourSection items={ingress} emptyText="No documents staged" />,
  );

  expect(screen.queryByRole("heading", { level: 2 })).toBeNull();
});

it("the empty-state text is unchanged", () => {
  renderWithProviders(
    <>
      <NeighbourSection items={[]} emptyText="No documents staged" />
      <NeighbourSection items={[]} emptyText="No documents staged" />
    </>,
  );

  expect(screen.getAllByText("No documents staged")).toHaveLength(2);
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

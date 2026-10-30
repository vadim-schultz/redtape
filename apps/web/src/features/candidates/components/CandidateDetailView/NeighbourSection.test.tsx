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

it("ingress section lists neighbour cards", () => {
  renderWithProviders(<NeighbourSection kind="ingress" items={ingress} />);

  const section = screen.getByRole("region", { name: "Ingress" });
  const links = within(section).getAllByRole("link");
  expect(links.map((link) => link.getAttribute("href"))).toEqual([
    "/candidates/n1",
    "/candidates/n2",
  ]);
  expect(within(section).getByText("Documents you need first")).toBeVisible();
  expect(within(links[0]).getByText("Condition: if born abroad")).toBeVisible();
  expect(within(links[1]).getByText("Optional")).toBeVisible();
  expect(within(links[0]).queryByText("Optional")).toBeNull();
});

it("egress section lists neighbour cards", () => {
  renderWithProviders(
    <>
      <NeighbourSection kind="ingress" items={ingress} />
      <NeighbourSection
        kind="egress"
        items={[neighbourFixture({ id: "e1", title: "Residence permit" })]}
      />
    </>,
  );

  const section = screen.getByRole("region", { name: "Egress" });
  expect(
    within(section).getByText("Documents that need this one"),
  ).toBeVisible();
  expect(within(section).getAllByRole("link")).toHaveLength(1);
  expect(within(section).getByText("Residence permit")).toBeVisible();
  expect(within(section).queryByText("Birth certificate")).toBeNull();
});

it("empty ingress and egress show the empty text", () => {
  renderWithProviders(
    <>
      <NeighbourSection kind="ingress" items={[]} />
      <NeighbourSection kind="egress" items={[]} />
    </>,
  );

  expect(screen.getByRole("heading", { name: "Ingress" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Egress" })).toBeInTheDocument();
  expect(screen.getAllByText("No documents staged")).toHaveLength(2);
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

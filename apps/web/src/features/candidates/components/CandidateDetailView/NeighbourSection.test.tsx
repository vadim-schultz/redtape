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

it("the ingress heading reads the plain-language text", () => {
  renderWithProviders(<NeighbourSection kind="ingress" items={ingress} />);

  const section = screen.getByRole("region", {
    name: "Documents you need first",
  });
  const links = within(section).getAllByRole("link");
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
      <NeighbourSection kind="ingress" items={ingress} />
      <NeighbourSection
        kind="egress"
        items={[neighbourFixture({ id: "e1", title: "Residence permit" })]}
      />
    </>,
  );

  const section = screen.getByRole("region", {
    name: "Documents that need this one",
  });
  expect(within(section).getAllByRole("link")).toHaveLength(1);
  expect(within(section).getByText("Residence permit")).toBeVisible();
  expect(within(section).queryByText("Birth certificate")).toBeNull();
  expect(screen.queryByText("Egress")).toBeNull();
});

it("the section renders no separate subtitle line", () => {
  renderWithProviders(<NeighbourSection kind="ingress" items={ingress} />);

  expect(screen.getAllByText("Documents you need first")).toHaveLength(1);
  const heading = screen.getByRole("heading", {
    name: "Documents you need first",
  });
  expect(heading.tagName).toBe("H2");
});

it("the empty-state text is unchanged", () => {
  renderWithProviders(
    <>
      <NeighbourSection kind="ingress" items={[]} />
      <NeighbourSection kind="egress" items={[]} />
    </>,
  );

  expect(
    screen.getByRole("heading", { name: "Documents you need first" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Documents that need this one" }),
  ).toBeInTheDocument();
  expect(screen.getAllByText("No documents staged")).toHaveLength(2);
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

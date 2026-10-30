import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { neighbourFixture } from "../../../../test/candidateFixtures";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import { FLOW_GEOMETRY, layoutFlow } from "../../utils/layoutFlow";
import FlowDiagram from "./FlowDiagram";

beforeEach(() => window.localStorage.setItem("locale", "en"));

function neighbours(prefix: string, count: number) {
  return Array.from({ length: count }, (_, index) =>
    neighbourFixture({ id: `${prefix}${index}`, title: `${prefix} ${index}` }),
  );
}

function candidate(ingress: number, egress: number) {
  return {
    title: "Passport",
    ingress: neighbours("in", ingress),
    egress: neighbours("out", egress),
  };
}

function svgOf(container: HTMLElement): SVGSVGElement {
  return container.querySelector("svg")!;
}

it("flow diagram renders a link and a path per neighbour", () => {
  const { container } = renderWithProviders(
    <FlowDiagram candidate={candidate(2, 3)} />,
  );

  const hrefs = screen
    .getAllByRole("link")
    .map((link) => link.getAttribute("href"));
  expect(hrefs).toEqual([
    "/candidates/in0",
    "/candidates/in1",
    "/candidates/out0",
    "/candidates/out1",
    "/candidates/out2",
  ]);
  expect(screen.getByText("Passport")).toBeVisible();
  const paths = container.querySelectorAll("path[marker-end]");
  expect(paths).toHaveLength(5);
  expect(container.querySelectorAll("path")).toHaveLength(6);
});

it("flow diagram keeps the centre card between ingress and egress in DOM order", () => {
  renderWithProviders(<FlowDiagram candidate={candidate(1, 1)} />);

  const texts = ["in 0", "Passport", "out 0"].map((text) =>
    screen.getByText(text),
  );
  const [first, middle, last] = texts;
  expect(
    first.compareDocumentPosition(middle) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
  expect(
    middle.compareDocumentPosition(last) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
});

it("flow diagram positions cards from the layout", () => {
  const { container } = renderWithProviders(
    <FlowDiagram candidate={candidate(2, 3)} />,
  );

  const layout = layoutFlow(2, 3);
  const svg = svgOf(container);
  expect(svg.getAttribute("width")).toBe(String(layout.width));
  expect(svg.getAttribute("height")).toBe(String(layout.height));
  const cards = container.querySelectorAll<HTMLElement>("[data-flow-node]");
  expect(cards).toHaveLength(layout.nodes.length);
  layout.nodes.forEach((node, index) => {
    expect(cards[index].style.left).toBe(`${node.x}px`);
    expect(cards[index].style.top).toBe(`${node.y}px`);
    expect(cards[index].style.width).toBe(`${FLOW_GEOMETRY.cardWidth}px`);
  });
});

it("flow diagram announces a text alternative", () => {
  const { container } = renderWithProviders(
    <FlowDiagram candidate={candidate(2, 3)} />,
  );

  const group = screen.getByRole("group", {
    name: "2 documents needed first, 3 documents that need this one",
  });
  expect(within(group).getAllByRole("link")).toHaveLength(5);
  expect(svgOf(container)).toHaveAttribute("aria-hidden", "true");
});

it("flow diagram shows the overflow note beyond the cap", () => {
  renderWithProviders(<FlowDiagram candidate={candidate(0, 20)} />);

  expect(screen.getAllByRole("link")).toHaveLength(12);
  expect(screen.getByText("+8 more, see the list above")).toBeVisible();
});

it("flow diagram shows no overflow note within the cap", () => {
  renderWithProviders(<FlowDiagram candidate={candidate(12, 12)} />);

  expect(screen.getAllByRole("link")).toHaveLength(24);
  expect(screen.queryByText(/more, see the list above/)).toBeNull();
});

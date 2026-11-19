import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import FlowGraph from "./FlowGraph";
import { layoutGraph } from "./layoutGraph";

const layout = layoutGraph(
  [{ id: "a" }, { id: "b" }, { id: "c" }],
  [
    { from: "a", to: "b" },
    { from: "a", to: "c", dashed: true },
  ],
);

it("FlowGraph · renders each stage through the render prop, in its place", () => {
  renderWithProviders(
    <FlowGraph
      layout={layout}
      label="Stages"
      renderNode={(id) => <span>{`${id} content`}</span>}
    />,
  );

  expect(screen.getByRole("group", { name: "Stages" })).toBeInTheDocument();
  for (const id of ["a", "b", "c"]) {
    expect(screen.getByText(`${id} content`)).toBeInTheDocument();
  }
  expect(
    screen.getByText("b content").closest("[data-graph-node]"),
  ).toHaveAttribute("data-graph-node", "b");
});

it("FlowGraph · draws one arrow per edge, and dashes the edge that asks for it", () => {
  const { container } = renderWithProviders(
    <FlowGraph layout={layout} label="Stages" renderNode={() => null} />,
  );

  const paths = container.querySelectorAll("path.graph-edge");
  expect(paths).toHaveLength(2);
  expect(paths[0].getAttribute("marker-end")).toMatch(/^url\(#graph-arrow-/);
  expect(
    container.querySelectorAll("path.graph-edge[stroke-dasharray]"),
  ).toHaveLength(1);
});

it("FlowGraph · an empty layout draws no stage and no edge", () => {
  const { container } = renderWithProviders(
    <FlowGraph
      layout={layoutGraph([], [])}
      label="Stages"
      renderNode={() => <span>stage</span>}
    />,
  );

  expect(screen.queryByText("stage")).not.toBeInTheDocument();
  expect(container.querySelectorAll("path.graph-edge")).toHaveLength(0);
});

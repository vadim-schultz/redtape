import { describe, expect, it } from "vitest";

import { layoutGraph, type GraphEdge, type GraphNode } from "./layoutGraph";

const NODES: GraphNode[] = [
  { id: "seed" },
  { id: "render" },
  { id: "extract" },
  { id: "llm" },
  { id: "capture" },
  { id: "embed" },
];

const EDGES: GraphEdge[] = [
  { from: "seed", to: "render" },
  { from: "render", to: "extract" },
  { from: "render", to: "llm" },
  { from: "llm", to: "capture" },
  { from: "llm", to: "embed" },
  { from: "render", to: "capture", dashed: true },
];

/** The placed node with `id`; a missing node fails the test with a clear message. */
function placed(layout: ReturnType<typeof layoutGraph>, id: string) {
  const node = layout.nodes.find((candidate) => candidate.id === id);
  if (!node) throw new Error(`no placed node ${id}`);
  return node;
}

describe("layoutGraph", () => {
  it("the layout places a stage after every stage it feeds", () => {
    const layout = layoutGraph(NODES, EDGES);

    for (const { from, to } of EDGES) {
      expect(placed(layout, to).layer).toBeGreaterThan(
        placed(layout, from).layer,
      );
    }
    expect(placed(layout, "seed").layer).toBe(0);
    expect(placed(layout, "capture").layer).toBe(3);
  });

  it("a cycle is rejected with an error", () => {
    const cycle: GraphEdge[] = [
      { from: "a", to: "b" },
      { from: "b", to: "a" },
    ];

    expect(() => layoutGraph([{ id: "a" }, { id: "b" }], cycle)).toThrow(
      /cycle/i,
    );
  });

  it("an edge to a stage that is not in the graph is rejected", () => {
    expect(() =>
      layoutGraph([{ id: "a" }], [{ from: "a", to: "missing" }]),
    ).toThrow(/unknown stage missing/);
  });

  it("the layout is deterministic for the same input", () => {
    const first = layoutGraph(NODES, EDGES);
    const second = layoutGraph(NODES, EDGES);

    expect(second).toEqual(first);
    expect(first.nodes.map(({ id, x, y }) => [id, x, y])).toEqual(
      second.nodes.map(({ id, x, y }) => [id, x, y]),
    );
  });

  it("lists the stages in topological order", () => {
    const layout = layoutGraph(NODES, EDGES);
    const ids = layout.nodes.map((node) => node.id);

    for (const { from, to } of EDGES) {
      expect(ids.indexOf(from)).toBeLessThan(ids.indexOf(to));
    }
  });

  it("a stage sits in the order of the stages that feed it", () => {
    const layout = layoutGraph(
      [{ id: "a" }, { id: "b" }, { id: "x" }, { id: "y" }],
      [
        { from: "a", to: "y" },
        { from: "b", to: "x" },
      ],
    );

    expect(placed(layout, "y").order).toBeLessThan(placed(layout, "x").order);
  });

  it("columns advance to the right and rows advance downwards", () => {
    const layout = layoutGraph(NODES, EDGES);

    expect(placed(layout, "render").x).toBeGreaterThan(
      placed(layout, "seed").x,
    );
    expect(placed(layout, "embed").y).toBeGreaterThan(
      placed(layout, "capture").y,
    );
  });

  it("a graph with no stages lays out to its padding alone", () => {
    const layout = layoutGraph([], []);

    expect(layout.nodes).toEqual([]);
    expect(layout.edges).toEqual([]);
    expect(layout.width).toBe(2 * layout.geometry.padding);
  });
});

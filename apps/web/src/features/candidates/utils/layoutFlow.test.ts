import { describe, expect, it } from "vitest";

import {
  FLOW_GEOMETRY,
  MAX_FLOW_NODES,
  layoutFlow,
  type FlowLayout,
  type FlowNode,
} from "./layoutFlow";

const G = FLOW_GEOMETRY;
const PITCH = G.cardHeight + G.rowGap;
const COLUMN_STEP = G.cardWidth + G.columnGap;

function column(layout: FlowLayout, role: FlowNode["role"]): FlowNode[] {
  return layout.nodes.filter((node) => node.role === role);
}

function midpoint(nodes: FlowNode[]): number {
  const first = nodes[0].y;
  const last = nodes[nodes.length - 1].y + G.cardHeight;
  return (first + last) / 2;
}

function centreOf(layout: FlowLayout): FlowNode {
  return column(layout, "centre")[0];
}

function numbersIn(d: string): string[] {
  return d.match(/[\d.]+/g) ?? [];
}

describe("layoutFlow columns", () => {
  it("layoutFlow places one column of three ingress cards", () => {
    const layout = layoutFlow(3, 1);

    const ingress = column(layout, "ingress");
    const top = ingress[0].y;
    expect(ingress.map((node) => node.y)).toEqual([
      top,
      top + PITCH,
      top + 2 * PITCH,
    ]);
    expect(ingress.every((node) => node.x === G.padding)).toBe(true);
    expect(midpoint(ingress)).toBe(centreOf(layout).y + G.cardHeight / 2);
  });

  it.each([
    [2, 5],
    [5, 2],
  ])(
    "layoutFlow centres the shorter column against the taller one (%i, %i)",
    (ingressCount, egressCount) => {
      const layout = layoutFlow(ingressCount, egressCount);

      const ingress = column(layout, "ingress");
      const egress = column(layout, "egress");
      expect(midpoint(ingress)).toBe(midpoint(egress));
      const tallest = Math.max(ingressCount, egressCount);
      const columnHeight = tallest * G.cardHeight + (tallest - 1) * G.rowGap;
      expect(layout.height).toBe(columnHeight + 2 * G.padding);
    },
  );

  it("layoutFlow with no ingress and no egress returns only the centre card", () => {
    const layout = layoutFlow(0, 0);

    expect(layout.nodes).toHaveLength(1);
    expect(layout.nodes[0].role).toBe("centre");
    expect(layout.paths).toEqual([]);
    expect(layout.height).toBe(G.cardHeight + 2 * G.padding);
  });

  it.each([
    [0, 3],
    [3, 0],
  ])(
    "layoutFlow with one side empty keeps the width (%i, %i)",
    (ingressCount, egressCount) => {
      const full = layoutFlow(3, 3);
      const sided = layoutFlow(ingressCount, egressCount);

      expect(sided.width).toBe(full.width);
      expect(sided.width).toBe(
        3 * G.cardWidth + 2 * G.columnGap + 2 * G.padding,
      );
      expect(centreOf(sided).x).toBe(centreOf(full).x);
      expect(centreOf(sided).x).toBe(G.padding + COLUMN_STEP);
      const egress = column(sided, "egress");
      expect(egress).toHaveLength(egressCount);
      egress.forEach((node) =>
        expect(node.x).toBe(G.padding + 2 * COLUMN_STEP),
      );
      expect(centreOf(sided).y).toBe(centreOf(full).y);
    },
  );

  it("layoutFlow lists nodes in DOM order: ingress, centre, egress", () => {
    const roles = layoutFlow(2, 2).nodes.map((node) => node.role);

    expect(roles).toEqual(["ingress", "ingress", "centre", "egress", "egress"]);
  });
});

describe("layoutFlow paths", () => {
  it("layoutFlow produces one path per edge with the right endpoints", () => {
    const layout = layoutFlow(3, 2);
    const centre = centreOf(layout);
    const centreMid = centre.y + G.cardHeight / 2;

    expect(layout.paths).toHaveLength(5);
    const ingressPaths = layout.paths.filter((p) => p.from === "ingress");
    ingressPaths.forEach((path) => {
      const card = column(layout, "ingress")[path.index];
      const start = [card.x + G.cardWidth, card.y + G.cardHeight / 2];
      const end = [centre.x - G.arrowInset, centreMid];
      expect(path.d).toMatch(new RegExp(`^M ${start[0]} ${start[1]} C `));
      expect(path.d).toMatch(new RegExp(` ${end[0]} ${end[1]}$`));
    });
    const egressPaths = layout.paths.filter((p) => p.from === "centre");
    expect(egressPaths).toHaveLength(2);
    egressPaths.forEach((path) => {
      const card = column(layout, "egress")[path.index];
      const end = [card.x - G.arrowInset, card.y + G.cardHeight / 2];
      expect(path.d).toMatch(
        new RegExp(`^M ${centre.x + G.cardWidth} ${centreMid} C `),
      );
      expect(path.d).toMatch(new RegExp(` ${end[0]} ${end[1]}$`));
    });
  });

  it("layoutFlow path data is a smooth cubic", () => {
    const shape =
      /^M [\d.]+ [\d.]+ C [\d.]+ [\d.]+, [\d.]+ [\d.]+, [\d.]+ [\d.]+$/;

    layoutFlow(3, 2).paths.forEach(({ d }) => {
      expect(d).toMatch(shape);
      const [x1, y1, c1x, c1y, c2x, c2y, x2, y2] = numbersIn(d).map(Number);
      expect(c1x).toBeCloseTo((x1 + x2) / 2, 1);
      expect(c2x).toBe(c1x);
      expect(c1y).toBe(y1);
      expect(c2y).toBe(y2);
    });
  });

  it("layoutFlow keeps a straight horizontal edge a valid cubic", () => {
    const layout = layoutFlow(1, 1);

    layout.paths.forEach(({ d }) => {
      const [, y1, , c1y, , c2y, , y2] = numbersIn(d).map(Number);
      expect([y1, c1y, c2y, y2]).toEqual([y1, y1, y1, y1]);
      expect(d).toMatch(
        /^M [\d.]+ [\d.]+ C [\d.]+ [\d.]+, [\d.]+ [\d.]+, [\d.]+ [\d.]+$/,
      );
    });
  });

  it("layoutFlow is deterministic and rounds to one decimal", () => {
    const odd = { cardHeight: 71, columnGap: 121, cardWidth: 219 };

    expect(layoutFlow(3, 4, odd)).toEqual(layoutFlow(3, 4, odd));
    layoutFlow(3, 4, odd).paths.forEach(({ d }) => {
      numbersIn(d).forEach((value) => expect(value).toMatch(/^\d+(\.\d)?$/));
    });
  });
});

describe("layoutFlow input and caps", () => {
  it.each([
    [-1, 0],
    [0, -1],
    [1.5, 0],
    [0, 1.5],
    [Number.NaN, 0],
  ])("layoutFlow rejects negative or non-integer counts (%d, %d)", (a, b) => {
    expect(() => layoutFlow(a, b)).toThrow(RangeError);
  });

  it("layoutFlow caps the drawn nodes and reports the hidden count", () => {
    const layout = layoutFlow(20, 3);

    expect(MAX_FLOW_NODES).toBe(12);
    expect(column(layout, "ingress")).toHaveLength(MAX_FLOW_NODES);
    expect(column(layout, "egress")).toHaveLength(3);
    expect(layout.paths).toHaveLength(MAX_FLOW_NODES + 3);
    expect(layout.hidden).toEqual({ ingress: 8, egress: 0 });
  });

  it("layoutFlow reports nothing hidden below the cap", () => {
    expect(layoutFlow(MAX_FLOW_NODES, MAX_FLOW_NODES).hidden).toEqual({
      ingress: 0,
      egress: 0,
    });
  });
});

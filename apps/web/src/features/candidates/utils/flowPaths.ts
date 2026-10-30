import type { FlowGeometry, FlowNode, FlowPath } from "./flowGeometry";

type Point = { x: number; y: number };

const round1 = (value: number): number => Math.round(value * 10) / 10;

function curve(from: Point, to: Point): string {
  const xm = round1((from.x + to.x) / 2);
  const [x1, y1, x2, y2] = [from.x, from.y, to.x, to.y].map(round1);
  return `M ${x1} ${y1} C ${xm} ${y1}, ${xm} ${y2}, ${x2} ${y2}`;
}

function edge(from: FlowNode, to: FlowNode, g: FlowGeometry): string {
  const start = { x: from.x + g.cardWidth, y: from.y + g.cardHeight / 2 };
  return curve(start, { x: to.x - g.arrowInset, y: to.y + g.cardHeight / 2 });
}

/** One cubic arrow per edge: ingress cards into the centre card, the centre card out to egress cards. */
export function flowPaths(nodes: FlowNode[], g: FlowGeometry): FlowPath[] {
  const centre = nodes.find((node) => node.role === "centre")!;
  const into = nodes.filter((n) => n.role === "ingress");
  const out = nodes.filter((n) => n.role === "egress");
  return [
    ...into.map((n) => ({
      from: "ingress" as const,
      index: n.index,
      d: edge(n, centre, g),
    })),
    ...out.map((n) => ({
      from: "centre" as const,
      index: n.index,
      d: edge(centre, n, g),
    })),
  ];
}

import {
  FLOW_GEOMETRY,
  type FlowGeometry,
  type FlowHidden,
  type FlowLayout,
  type FlowNode,
  type FlowRole,
} from "./flowGeometry";

import { flowPaths } from "./flowPaths";

export * from "./flowGeometry";

type Frame = { g: FlowGeometry; inner: number; x: Record<FlowRole, number> };

function assertCount(count: number): void {
  if (Number.isInteger(count) && count >= 0) return;
  throw new RangeError(`Flow count must be a non-negative integer: ${count}`);
}

function columnHeight(count: number, g: FlowGeometry): number {
  return count * g.cardHeight + Math.max(count - 1, 0) * g.rowGap;
}

function makeFrame(drawn: FlowHidden, g: FlowGeometry): Frame {
  const tallest = Math.max(
    columnHeight(drawn.ingress, g),
    columnHeight(drawn.egress, g),
  );
  const step = g.cardWidth + g.columnGap;
  const x = {
    ingress: g.padding,
    centre: g.padding + step,
    egress: g.padding + 2 * step,
  };
  return { g, inner: Math.max(tallest, g.cardHeight), x };
}

function columnTop(frame: Frame, count: number): number {
  return frame.g.padding + (frame.inner - columnHeight(count, frame.g)) / 2;
}

function column(frame: Frame, role: FlowRole, count: number): FlowNode[] {
  const pitch = frame.g.cardHeight + frame.g.rowGap;
  const top = columnTop(frame, count);
  return Array.from({ length: count }, (_, index) => ({
    role,
    index,
    x: frame.x[role],
    y: top + index * pitch,
  }));
}

function drawnCounts(ingress: number, egress: number, g: FlowGeometry) {
  return {
    ingress: Math.min(ingress, g.maxNodes),
    egress: Math.min(egress, g.maxNodes),
  };
}

function flowNodes(frame: Frame, drawn: FlowHidden): FlowNode[] {
  return [
    ...column(frame, "ingress", drawn.ingress),
    ...column(frame, "centre", 1),
    ...column(frame, "egress", drawn.egress),
  ];
}

function flowWidth(g: FlowGeometry): number {
  return 3 * g.cardWidth + 2 * g.columnGap + 2 * g.padding;
}

/**
 * Where every card and arrow of the flow diagram goes. Pure: no DOM, no measuring.
 * Counts beyond `maxNodes` are not drawn and come back as `hidden`.
 */
export function layoutFlow(
  ingressCount: number,
  egressCount: number,
  overrides: Partial<FlowGeometry> = {},
): FlowLayout {
  [ingressCount, egressCount].forEach(assertCount);
  const g = { ...FLOW_GEOMETRY, ...overrides };
  const drawn = drawnCounts(ingressCount, egressCount, g);
  const frame = makeFrame(drawn, g);
  const nodes = flowNodes(frame, drawn);
  const hidden = {
    ingress: ingressCount - drawn.ingress,
    egress: egressCount - drawn.egress,
  };
  const height = frame.inner + 2 * g.padding;
  return {
    width: flowWidth(g),
    height,
    nodes,
    paths: flowPaths(nodes, g),
    hidden,
  };
}

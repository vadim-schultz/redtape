import { NEIGHBOUR_CARD_HEIGHT } from "./neighbourCard";

/** Most cards drawn per side; the lists above the diagram stay complete. */
export const MAX_FLOW_NODES = 12;

export type FlowGeometry = {
  cardWidth: number;
  cardHeight: number;
  rowGap: number;
  columnGap: number;
  padding: number;
  /** Arrow ends stop this far short of a card so the arrowhead is not hidden. */
  arrowInset: number;
  maxNodes: number;
};

/** The one set of numbers that cards and paths are both placed by. */
export const FLOW_GEOMETRY: FlowGeometry = {
  cardWidth: 220,
  cardHeight: NEIGHBOUR_CARD_HEIGHT,
  rowGap: 16,
  columnGap: 120,
  padding: 8,
  arrowInset: 6,
  maxNodes: MAX_FLOW_NODES,
};

export type FlowSide = "ingress" | "egress";
export type FlowRole = FlowSide | "centre";
export type FlowNode = { role: FlowRole; index: number; x: number; y: number };
export type FlowPath = { from: "ingress" | "centre"; index: number; d: string };
export type FlowHidden = Record<FlowSide, number>;
export type FlowLayout = {
  width: number;
  height: number;
  nodes: FlowNode[];
  paths: FlowPath[];
  hidden: FlowHidden;
};

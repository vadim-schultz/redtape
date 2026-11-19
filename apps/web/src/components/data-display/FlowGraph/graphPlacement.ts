import type { GraphGeometry, PlacedNode } from "./graphTypes";

/** The height of one column of `count` boxes, with the gaps between them. */
export function columnHeight(count: number, g: GraphGeometry): number {
  return count * g.nodeHeight + Math.max(count - 1, 0) * g.rowGap;
}

/** The height of the tallest column; an empty graph has none. */
export function tallestColumn(
  rows: readonly (readonly string[])[],
  g: GraphGeometry,
): number {
  return Math.max(0, ...rows.map((row) => columnHeight(row.length, g)));
}

/** Place every stage: columns by layer, rows by order, each column centred on the tallest one. */
export function placeNodes(
  rows: readonly (readonly string[])[],
  g: GraphGeometry,
): PlacedNode[] {
  const tallest = tallestColumn(rows, g);
  return rows.flatMap((row, layer) => {
    const top = g.padding + (tallest - columnHeight(row.length, g)) / 2;
    return row.map((id, order) => ({
      id,
      layer,
      order,
      x: g.padding + layer * (g.nodeWidth + g.columnGap),
      y: top + order * (g.nodeHeight + g.rowGap),
    }));
  });
}

/** The canvas size: the columns across, and the tallest column down, each with the padding around it. */
export function canvasSize(
  columns: number,
  tallest: number,
  g: GraphGeometry,
): { width: number; height: number } {
  const across = columns * g.nodeWidth + Math.max(columns - 1, 0) * g.columnGap;
  return { width: across + 2 * g.padding, height: tallest + 2 * g.padding };
}

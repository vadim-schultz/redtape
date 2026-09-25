import type { MatrixCell } from "../types";

export function cellKey(domain: string, situation: string): string {
  return `${domain}|${situation}`;
}

export function buildCellIndex(cells: MatrixCell[]): Map<string, number> {
  return new Map(cells.map((c) => [cellKey(c.domain, c.situation), c.count]));
}

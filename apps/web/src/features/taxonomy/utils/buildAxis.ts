import type { AxisTotal, MatrixAxisItem, Term } from "../types";

/**
 * Terms present in the matrix response, in taxonomy order. Totals are the
 * API's distinct-document counts, never summed from cells.
 */
export function buildAxis(
  terms: Term[],
  totals: AxisTotal[],
): MatrixAxisItem[] {
  const byCode = new Map(totals.map((t) => [t.code, t.count]));

  return terms
    .filter((term) => byCode.has(term.code))
    .map((term) => ({
      code: term.code,
      name: term.name,
      total: byCode.get(term.code) ?? 0,
    }));
}

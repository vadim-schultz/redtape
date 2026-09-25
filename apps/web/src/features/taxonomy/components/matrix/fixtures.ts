import type { MatrixAxisItem } from "../../types";

export const domains: MatrixAxisItem[] = [
  { code: "wohnen", name: "Housing", total: 5 },
  { code: "verkehr", name: "Traffic", total: 2 },
];

export const situations: MatrixAxisItem[] = [
  { code: "umzug", name: "Moving house", total: 7 },
  { code: "auto", name: "My car", total: 2 },
];

/** umzug × wohnen = 5, umzug × verkehr = 4 (sums to 9, but umzug's total is 7). */
export const cellCounts = new Map<string, number>([
  ["wohnen|umzug", 5],
  ["verkehr|umzug", 4],
  ["verkehr|auto", 2],
]);

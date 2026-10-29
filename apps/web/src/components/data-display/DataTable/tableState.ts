import type { DataTableStates } from "./types";

export type TableState = "loading" | "error" | "empty" | "populated";

/** Which state the body shows; an empty result only counts when it has a slot. */
export function resolveTableState(
  { status, empty }: DataTableStates,
  rowCount: number,
): TableState {
  const rules: [boolean, TableState][] = [
    [status?.isLoading === true, "loading"],
    [status?.isError === true, "error"],
    [rowCount === 0 && empty !== undefined, "empty"],
  ];
  return rules.find(([applies]) => applies)?.[1] ?? "populated";
}

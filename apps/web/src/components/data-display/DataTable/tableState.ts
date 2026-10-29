import type { DataTableStates } from "./types";

export type TableState = "loading" | "error" | "empty" | "populated";

/**
 * Which state the body shows. A failure only replaces the body when there are
 * no rows to keep; an empty result only counts when it has a slot.
 */
export function resolveTableState(
  { status, empty }: DataTableStates,
  rowCount: number,
): TableState {
  const rules: [boolean, TableState][] = [
    [status?.isLoading === true, "loading"],
    [status?.isError === true && rowCount === 0, "error"],
    [rowCount === 0 && empty !== undefined, "empty"],
  ];
  return rules.find(([applies]) => applies)?.[1] ?? "populated";
}

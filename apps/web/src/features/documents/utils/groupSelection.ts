import type { GroupedTerm } from "../../taxonomy/types";

/** The life-area and life-situation chips in effect; a group and its situations never coexist. */
export type GroupSelection = {
  groups: string[];
  situations: string[];
};

export function toggled(codes: string[], code: string): string[] {
  return codes.includes(code)
    ? codes.filter((c) => c !== code)
    : [...codes, code];
}

function groupOf(code: string, situations: GroupedTerm[]): string | undefined {
  return situations.find((s) => s.code === code)?.group_code;
}

/** Selecting a group takes over its situations; deselecting only removes the group. */
export function toggleGroupSelection(
  selection: GroupSelection,
  group: string,
  situations: GroupedTerm[],
): GroupSelection {
  const groups = toggled(selection.groups, group);
  if (!groups.includes(group)) return { ...selection, groups };
  return {
    groups,
    situations: selection.situations.filter(
      (code) => groupOf(code, situations) !== group,
    ),
  };
}

/** Selecting a situation narrows its group away; deselecting only removes the situation. */
export function toggleSituationSelection(
  selection: GroupSelection,
  code: string,
  situations: GroupedTerm[],
): GroupSelection {
  const next = toggled(selection.situations, code);
  const group = groupOf(code, situations);
  return {
    groups: selection.groups.filter((g) => g !== group),
    situations: next,
  };
}

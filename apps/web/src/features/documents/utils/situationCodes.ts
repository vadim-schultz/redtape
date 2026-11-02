import type { GroupedTerm } from "../../taxonomy/types";
import type { GroupSelection } from "./groupSelection";

/** The situation codes a request filters by: the selected situations plus every
 * situation of a selected group. Unknown groups and unloaded situations add nothing. */
export function situationCodes(
  selection: GroupSelection,
  situations: GroupedTerm[],
): string[] {
  const ofGroups = situations
    .filter((s) => selection.groups.includes(s.group_code))
    .map((s) => s.code);
  return [...new Set([...selection.situations, ...ofGroups])];
}

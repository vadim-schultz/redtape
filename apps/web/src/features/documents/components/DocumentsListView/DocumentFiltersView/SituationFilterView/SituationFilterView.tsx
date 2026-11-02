import { useState } from "react";
import { HStack, VStack } from "@chakra-ui/react";

import type { DocumentFilters as DocumentFiltersState } from "../../../../hooks/useDocumentFilters";
import type { GroupedTerm, Term } from "../../../../../taxonomy/types";
import FilterChip from "../FilterChip";

export interface SituationFilterViewProps {
  groups: Term[];
  situations: GroupedTerm[];
  filters: DocumentFiltersState;
}

/** The group a deep link opens: the first selected known group, else the group of the first
 * selected situation; `null` for none, or while the taxonomy queries are still loading, so a
 * deep link's group can still auto-expand once they resolve. */
function linkedGroup(
  groups: Term[],
  situations: GroupedTerm[],
  filters: DocumentFiltersState,
): string | null {
  const selectedArea = groups.find((g) => filters.groups.includes(g.code));
  const selectedSituation = situations.find((s) =>
    filters.situations.includes(s.code),
  );
  return selectedArea?.code ?? selectedSituation?.group_code ?? null;
}

/** True when a situation of `group` is selected on its own, narrower than the whole area. */
function hasSubSelection(
  group: string,
  situations: GroupedTerm[],
  selected: string[],
): boolean {
  return situations.some(
    (s) => s.group_code === group && selected.includes(s.code),
  );
}

export default function SituationFilterView({
  groups,
  situations,
  filters,
}: SituationFilterViewProps) {
  const [touchedGroup, setTouchedGroup] = useState<string | null | undefined>(
    undefined,
  );
  const expandedGroup =
    touchedGroup === undefined
      ? linkedGroup(groups, situations, filters)
      : touchedGroup;
  const visible = situations.filter((s) => s.group_code === expandedGroup);

  // Selecting an area expands it; deselecting leaves the row as it is.
  const toggleGroup = (code: string, selected: boolean) => {
    filters.toggleGroup(code);
    if (!selected) setTouchedGroup(code);
  };

  return (
    <VStack align="stretch" gap={2}>
      <HStack wrap="wrap" gap={2}>
        {groups.map((group) => {
          const selected = filters.groups.includes(group.code);
          return (
            <FilterChip
              key={group.code}
              label={group.name}
              tone="group"
              pressed={selected}
              partial={hasSubSelection(
                group.code,
                situations,
                filters.situations,
              )}
              onToggle={() => toggleGroup(group.code, selected)}
            />
          );
        })}
      </HStack>
      {visible.length > 0 ? (
        <HStack wrap="wrap" gap={2}>
          {visible.map((situation) => (
            <FilterChip
              key={situation.code}
              label={situation.name}
              tone="sub"
              pressed={filters.situations.includes(situation.code)}
              onToggle={() => filters.toggleSituation(situation.code)}
            />
          ))}
        </HStack>
      ) : null}
    </VStack>
  );
}

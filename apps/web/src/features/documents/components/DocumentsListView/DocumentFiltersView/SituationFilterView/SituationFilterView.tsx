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

/** The group of the first selected situation; `undefined` once the groups/situations queries
 * are still loading, so a deep link's group can still auto-expand once they resolve. */
function selectedGroup(
  situations: GroupedTerm[],
  selected: string[],
): string | null {
  const selectedSituation = situations.find((s) => selected.includes(s.code));
  return selectedSituation?.group_code ?? null;
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
      ? selectedGroup(situations, filters.situations)
      : touchedGroup;
  const visible = situations.filter((s) => s.group_code === expandedGroup);

  return (
    <VStack align="stretch" gap={2}>
      <HStack wrap="wrap" gap={2}>
        {groups.map((group) => (
          <FilterChip
            key={group.code}
            label={group.name}
            // A group is pure navigation, never itself a filter (architecture §4) — its
            // chip never reports `pressed`; the revealed situation row is the expand signal.
            pressed={false}
            onToggle={() =>
              setTouchedGroup(expandedGroup === group.code ? null : group.code)
            }
          />
        ))}
      </HStack>
      {visible.length > 0 ? (
        <HStack wrap="wrap" gap={2}>
          {visible.map((situation) => (
            <FilterChip
              key={situation.code}
              label={situation.name}
              pressed={filters.situations.includes(situation.code)}
              onToggle={() => filters.toggleSituation(situation.code)}
            />
          ))}
        </HStack>
      ) : null}
    </VStack>
  );
}

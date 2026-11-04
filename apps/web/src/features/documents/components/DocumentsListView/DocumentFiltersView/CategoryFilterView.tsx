import { HStack, VStack } from "@chakra-ui/react";
import { useState } from "react";

import type { CategoryNode } from "../../../../../taxonomy/types";
import type { DocumentFilters } from "../../../hooks/useDocumentFilters";
import FilterChip from "./FilterChip";

export interface CategoryFilterViewProps {
  categories: CategoryNode[];
  filters: DocumentFilters;
}

function rootForSelection(
  categories: CategoryNode[],
  selected: string[],
): string | null {
  const selectedRoot = categories.find((root) => selected.includes(root.code));
  if (selectedRoot) return selectedRoot.code;

  return (
    categories.find((root) =>
      root.children.some((child) => selected.includes(child.code)),
    )?.code ?? null
  );
}

/** Render roots and the children of the currently expanded root. */
export default function CategoryFilterView({
  categories,
  filters,
}: CategoryFilterViewProps) {
  const [touchedRoot, setTouchedRoot] = useState<string | null | undefined>();
  const expandedRoot =
    touchedRoot === undefined
      ? rootForSelection(categories, filters.categories)
      : touchedRoot;
  const root = categories.find((candidate) => candidate.code === expandedRoot);

  return (
    <VStack align="stretch" gap={2}>
      <HStack wrap="wrap" gap={2}>
        {categories.map((category) => {
          const selected = filters.categories.includes(category.code);
          return (
            <FilterChip
              key={category.code}
              label={category.name}
              pressed={selected}
              onToggle={() => {
                filters.toggleCategory(category.code);
                if (!selected) setTouchedRoot(category.code);
              }}
            />
          );
        })}
      </HStack>
      {root?.children.length ? (
        <HStack wrap="wrap" gap={2}>
          {root.children.map((category) => (
            <FilterChip
              key={category.code}
              label={category.name}
              tone="sub"
              pressed={filters.categories.includes(category.code)}
              onToggle={() =>
                filters.toggleCategory(category.code, category.parent_code)
              }
            />
          ))}
        </HStack>
      ) : null}
    </VStack>
  );
}

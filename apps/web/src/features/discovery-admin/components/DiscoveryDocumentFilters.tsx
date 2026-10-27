import { HStack } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryDocumentFilters as FiltersState } from "../hooks/useDiscoveryDocumentFilters";
import type {
  DiscoveryCandidateSort,
  DiscoveryMentionRole,
  DiscoverySource,
} from "../types";
import DiscoveryDocumentSearch from "./DiscoveryDocumentSearch";
import FilterSelect, { type FilterOption } from "./FilterSelect";

const NAMESPACE = "discovery_admin.documents";
const ROLES: DiscoveryMentionRole[] = ["required", "form"];
const SOURCES: DiscoverySource[] = [
  "govdata",
  "pvog",
  "fim",
  "leika",
  "manual",
];
const SORTS: DiscoveryCandidateSort[] = [
  "mentions_desc",
  "title_asc",
  "newest",
];
const MINIMUMS = [1, 2, 5, 10];

function plain(values: string[]): FilterOption[] {
  return values.map((value) => ({ value, label: value }));
}

function orNull<T extends string>(value: string): T | null {
  return value === "" ? null : (value as T);
}

/** Search, filter and sort controls of the documents list. */
export default function DiscoveryDocumentFilters({
  filters,
}: {
  filters: FiltersState;
}) {
  const { t } = useLocale();
  const label = (key: string) => t(`${NAMESPACE}.${key}`);
  const withAll = (key: string, options: FilterOption[]) => [
    { value: "", label: label(key) },
    ...options,
  ];

  return (
    <HStack gap={4} flexWrap="wrap">
      <DiscoveryDocumentSearch filters={filters} />
      <FilterSelect
        label={label("filter_min_mentions")}
        value={String(filters.minMentions ?? "")}
        options={withAll(
          "min_mentions_any",
          MINIMUMS.map((count) => ({
            value: String(count),
            label: t(`${NAMESPACE}.min_mentions_option`, { count }),
          })),
        )}
        onChange={(value) =>
          filters.setFilters({
            minMentions: value === "" ? null : Number(value),
          })
        }
      />
      <FilterSelect
        label={label("filter_role")}
        value={filters.role ?? ""}
        options={withAll(
          "role_all",
          ROLES.map((role) => ({ value: role, label: label(`role_${role}`) })),
        )}
        onChange={(value) =>
          filters.setFilters({ role: orNull<DiscoveryMentionRole>(value) })
        }
      />
      <FilterSelect
        label={label("filter_source")}
        value={filters.source ?? ""}
        options={withAll("source_all", plain(SOURCES))}
        onChange={(value) =>
          filters.setFilters({ source: orNull<DiscoverySource>(value) })
        }
      />
      <FilterSelect
        label={label("filter_sort")}
        value={filters.sort}
        options={SORTS.map((sort) => ({
          value: sort,
          label: label(`sort_${sort}`),
        }))}
        onChange={(value) =>
          filters.setFilters({ sort: value as DiscoveryCandidateSort })
        }
      />
    </HStack>
  );
}

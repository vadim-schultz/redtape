import { HStack } from "@chakra-ui/react";

import {
  useLocale,
  type LocaleContextValue,
} from "../../../contexts/LocaleContext";
import type { CandidateList } from "../hooks/useCandidateListState";
import type { CandidateFilterKey } from "../types";
import DiscoveryDocumentSearch from "./DiscoveryDocumentSearch";
import FilterSelect, { type FilterOption } from "./FilterSelect";

const NAMESPACE = "discovery_admin.documents";
const ROLES = ["required", "form", "issued"];
const SOURCES = ["govdata", "pvog", "fim", "leika", "manual"];
const MINIMUMS = [1, 2, 5, 10];

interface FilterField {
  key: CandidateFilterKey;
  label: string;
  options: FilterOption[];
}

function plain(values: string[]): FilterOption[] {
  return values.map((value) => ({ value, label: value }));
}

/** A select bound to one filter key; the empty option clears it. */
function FieldSelect({
  list,
  field,
}: {
  list: CandidateList;
  field: FilterField;
}) {
  return (
    <FilterSelect
      label={field.label}
      value={String(list.state.filters[field.key] ?? "")}
      options={field.options}
      onChange={(value) => list.setFilter(field.key, value || undefined)}
    />
  );
}

function filterFields(t: LocaleContextValue["t"]): FilterField[] {
  const label = (key: string) => t(`${NAMESPACE}.${key}`);
  const withAll = (key: string, options: FilterOption[]) => [
    { value: "", label: label(key) },
    ...options,
  ];
  return [
    {
      key: "min_mentions",
      label: label("filter_min_mentions"),
      options: withAll(
        "min_mentions_any",
        MINIMUMS.map((count) => ({
          value: String(count),
          label: t(`${NAMESPACE}.min_mentions_option`, { count }),
        })),
      ),
    },
    {
      key: "role",
      label: label("filter_role"),
      options: withAll(
        "role_all",
        ROLES.map((role) => ({ value: role, label: label(`role_${role}`) })),
      ),
    },
    {
      key: "source",
      label: label("filter_source"),
      options: withAll("source_all", plain(SOURCES)),
    },
  ];
}

/** Search and filter controls of the documents list; sorting lives in the table header. */
export default function DiscoveryDocumentFilters({
  list,
}: {
  list: CandidateList;
}) {
  const { t } = useLocale();

  return (
    <HStack gap={4} flexWrap="wrap">
      <DiscoveryDocumentSearch list={list} />
      {filterFields(t).map((field) => (
        <FieldSelect key={field.key} list={list} field={field} />
      ))}
    </HStack>
  );
}

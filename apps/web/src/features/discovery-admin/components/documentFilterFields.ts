import type { LocaleContextValue } from "../../../contexts/LocaleContext";
import { DISCOVERY_SOURCES } from "../types/listValues";
import type { CandidateFilterKey } from "../types";
import { plainOptions } from "./columns/filterOptions";
import type { FilterOption } from "./FilterSelect";

const NAMESPACE = "discovery_admin.documents";
const ROLES = ["required", "form", "issued"];
const MINIMUMS = [1, 2, 5, 10];

/** One select of the documents toolbar: the filter key it sets, its name and its choices. */
export interface FilterField {
  key: CandidateFilterKey;
  label: string;
  options: FilterOption[];
}

export function filterFields(t: LocaleContextValue["t"]): FilterField[] {
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
      options: withAll("source_all", plainOptions(DISCOVERY_SOURCES)),
    },
  ];
}

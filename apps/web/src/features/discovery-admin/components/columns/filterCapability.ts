import type {
  FilterCapability,
  FilterOperator,
  FilterOption,
} from "../../../../components/data-display/DataTable";

/** What a column declares about its filter: the server key, the control label, and the allowed values. */
export interface FilterCapabilitySpec<FilterKey extends string> {
  key: FilterKey;
  label: string;
  options: readonly FilterOption[];
  /** The operator the server applies; equality unless the filter is a bound such as "at least". */
  operator?: FilterOperator;
}

/** Build a column's filter capability from its spec; every admin column filter goes through here. */
export function filterCapability<FilterKey extends string>({
  key,
  label,
  options,
  operator = "eq",
}: FilterCapabilitySpec<FilterKey>): FilterCapability<FilterKey> {
  return { key, operators: [operator], label, options };
}

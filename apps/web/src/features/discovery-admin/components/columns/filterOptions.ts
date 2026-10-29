import type { FilterOption } from "../../../../components/data-display/DataTable";

/** Options whose label is the raw value, for enums that have no translation. */
export function plainOptions(values: readonly string[]): FilterOption[] {
  return values.map((value) => ({ value, label: value }));
}

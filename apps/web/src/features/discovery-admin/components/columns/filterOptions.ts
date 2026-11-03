import type { FilterOption } from "../../../../components/data-display/DataTable";
import { translateOrRaw } from "../../utils/translateOrRaw";

/** Options whose label is the raw value, for enums that have no translation. */
export function plainOptions(values: readonly string[]): FilterOption[] {
  return values.map((value) => ({ value, label: value }));
}

/** Options labelled through `discovery_admin.values.<prefix>_<value>`, raw when untranslated. */
export function enumOptions(
  t: (key: string) => string,
  prefix: string,
  values: readonly string[],
): FilterOption[] {
  return values.map((value) => ({
    value,
    label: translateOrRaw(
      t,
      `discovery_admin.values.${prefix}_${value}`,
      value,
    ),
  }));
}

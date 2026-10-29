import type {
  AppliedFilters,
  DataTableColumn,
  FilterCapability,
} from "./types";

/** One applied filter as the summary shows it. */
export interface ActiveFilter<FilterKey extends string> {
  key: FilterKey;
  label: string;
  display: string;
}

function displayOf<FilterKey extends string>(
  { options }: FilterCapability<FilterKey>,
  value: string,
): string {
  return options?.find((option) => option.value === value)?.label ?? value;
}

/** The applied value of one filter key as text; empty when it is not applied. */
export function appliedValue<FilterKey extends string>(
  applied: AppliedFilters<FilterKey> | undefined,
  key: FilterKey,
): string {
  return String(applied?.[key] ?? "");
}

/** The filters in effect, in column order; empty values and undeclared keys do not count. */
export function activeFilters<
  Row,
  SortKey extends string,
  FilterKey extends string,
>(
  columns: readonly DataTableColumn<Row, SortKey, FilterKey>[],
  applied: AppliedFilters<FilterKey> | undefined,
): ActiveFilter<FilterKey>[] {
  return columns.flatMap(({ filter }) => {
    const value = filter && appliedValue(applied, filter.key);
    if (!filter || !value) return [];
    return [
      {
        key: filter.key,
        label: filter.label,
        display: displayOf(filter, value),
      },
    ];
  });
}

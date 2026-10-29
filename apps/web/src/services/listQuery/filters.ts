import type { FilterValue } from "./types";

/** A filter parser accepting only the listed values; anything else is rejected. */
export function oneOfFilter<T extends string>(values: readonly T[]) {
  return (raw: string): FilterValue | undefined =>
    values.find((value) => value === raw);
}

/** A filter parser accepting integers of at least `minimum`; anything else is rejected. */
export function minIntFilter(minimum: number) {
  return (raw: string): FilterValue | undefined => {
    const value = raw.trim() === "" ? NaN : Number(raw);
    return Number.isInteger(value) && value >= minimum ? value : undefined;
  };
}

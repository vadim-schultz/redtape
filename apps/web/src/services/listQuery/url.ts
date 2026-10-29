import { filterParam, toListParams } from "./params";
import type {
  FilterValue,
  ListQuerySpec,
  ListQueryState,
  SortOrder,
} from "./types";

const OWNED_KEYS = new Set(["offset", "limit", "sort_by", "sort_order", "q"]);

type Spec<S extends string, F extends string> = ListQuerySpec<S, F>;

function intInRange(
  raw: string | null,
  min: number,
  max: number,
  fallback: number,
) {
  const value = raw === null || raw.trim() === "" ? NaN : Number(raw);
  return Number.isInteger(value) && value >= min && value <= max
    ? value
    : fallback;
}

function parseFilters<S extends string, F extends string>(
  params: URLSearchParams,
  spec: Spec<S, F>,
): Partial<Record<F, FilterValue>> {
  const filters: Partial<Record<F, FilterValue>> = {};
  for (const key of Object.keys(spec.filters) as F[]) {
    const raw = params.get(filterParam(key));
    const value = raw === null ? undefined : spec.filters[key](raw);
    if (value !== undefined) filters[key] = value;
  }
  return filters;
}

function parseSort<S extends string>(
  params: URLSearchParams,
  keys: readonly S[],
): { sortBy?: S; sortOrder?: SortOrder } {
  const sortBy = keys.find((key) => key === params.get("sort_by"));
  if (!sortBy) return {};
  return {
    sortBy,
    sortOrder: params.get("sort_order") === "desc" ? "desc" : "asc",
  };
}

/** Parse URL state purely; every invalid value falls back to its default. */
export function parseListUrl<S extends string, F extends string>(
  params: URLSearchParams,
  spec: Spec<S, F>,
): ListQueryState<S, F> {
  return {
    offset: intInRange(params.get("offset"), 0, Number.MAX_SAFE_INTEGER, 0),
    limit: intInRange(params.get("limit"), 1, spec.maxLimit, spec.defaultLimit),
    ...parseSort(params, spec.sortKeys),
    search: params.get("q")?.trim() || undefined,
    filters: parseFilters(params, spec),
  };
}

function isOwned(key: string): boolean {
  return OWNED_KEYS.has(key) || key.startsWith("filter[");
}

function isDefault(
  key: string,
  value: string | number,
  spec: Spec<string, string>,
) {
  return (
    (key === "offset" && value === 0) ||
    (key === "limit" && value === spec.defaultLimit)
  );
}

/** Write a state into `base`, replacing the list parameters and keeping all others; defaults are omitted. */
export function serializeListUrl<S extends string, F extends string>(
  state: ListQueryState<S, F>,
  spec: Spec<S, F>,
  base: URLSearchParams = new URLSearchParams(),
): URLSearchParams {
  const next = new URLSearchParams(
    [...base.entries()].filter(([key]) => !isOwned(key)),
  );
  for (const [key, value] of Object.entries(toListParams(state))) {
    if (!isDefault(key, value, spec)) next.set(key, String(value));
  }
  return next;
}

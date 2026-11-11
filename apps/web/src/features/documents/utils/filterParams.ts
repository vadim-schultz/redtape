import type { CategoryNode } from "../../taxonomy/types";
import { flattenCategories } from "../../../utils/categoryTree";

/** The URL params the chips are stored in. */
export const FILTER_PARAMS = ["category"] as const;

/** One chip axis of the documents list URL. */
export type FilterAxis = (typeof FILTER_PARAMS)[number];

function toggled(codes: string[], code: string): string[] {
  return codes.includes(code)
    ? codes.filter((candidate) => candidate !== code)
    : [...codes, code];
}

/** The distinct, non-empty codes of `axis` in URL order. */
export function readCodes(params: URLSearchParams, axis: FilterAxis): string[] {
  return [...new Set(params.getAll(axis).filter(Boolean))];
}

/** Read only category codes that exist in the loaded canonical tree. */
export function readValidCategoryCodes(
  params: URLSearchParams,
  taxonomy: CategoryNode[],
): string[] {
  const known = new Set(flattenCategories(taxonomy).map((node) => node.code));
  return readCodes(params, "category").filter((code) => known.has(code));
}

/** Sort params the page no longer reads; a stale link may still carry them, and they are dropped on the next change. */
const RETIRED_SORT_PARAMS = ["sort_by", "sort_order"];

/** A copy of `params` without `names`; any change of the filters also leaves the current page and drops retired sort params. */
export function withoutParams(
  params: URLSearchParams,
  names: string[],
): URLSearchParams {
  const next = new URLSearchParams(params);
  [...names, "offset", ...RETIRED_SORT_PARAMS].forEach((name) =>
    next.delete(name),
  );
  return next;
}

function withCodes(
  params: URLSearchParams,
  axis: FilterAxis,
  codes: string[],
): URLSearchParams {
  const next = withoutParams(params, [axis]);
  codes.forEach((code) => next.append(axis, code));
  return next;
}

/** The selection after toggling `code`; picking a child also drops its selected parent. */
function codesAfterToggle(
  selected: string[],
  code: string,
  parentCode?: string | null,
): string[] {
  const next = toggled(selected, code);
  if (!parentCode || selected.includes(code)) return next;
  return next.filter((candidate) => candidate !== parentCode);
}

/** Toggle one canonical category without adding a legacy axis alias. */
export function withToggledCategory(
  params: URLSearchParams,
  code: string,
  parentCode?: string | null,
): URLSearchParams {
  const selected = readCodes(params, "category");
  return withCodes(
    params,
    "category",
    codesAfterToggle(selected, code, parentCode),
  );
}

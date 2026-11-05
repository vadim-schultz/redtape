import type { CategoryNode } from "../../taxonomy/types";

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

function flattenCategoryCodes(nodes: CategoryNode[]): Set<string> {
  return new Set(
    nodes.flatMap((node) => [
      node.code,
      ...flattenCategoryCodes(node.children),
    ]),
  );
}

/** Read only category codes that exist in the loaded canonical tree. */
export function readValidCategoryCodes(
  params: URLSearchParams,
  taxonomy: CategoryNode[],
): string[] {
  const known = flattenCategoryCodes(taxonomy);
  return readCodes(params, "category").filter((code) => known.has(code));
}

/** A copy of `params` without `names`; any change of the filters also leaves the current page. */
export function withoutParams(
  params: URLSearchParams,
  names: string[],
): URLSearchParams {
  const next = new URLSearchParams(params);
  [...names, "offset"].forEach((name) => next.delete(name));
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

/** Toggle one canonical category without adding a legacy axis alias. */
export function withToggledCategory(
  params: URLSearchParams,
  code: string,
  parentCode?: string | null,
): URLSearchParams {
  const selected = readCodes(params, "category");
  const next = toggled(selected, code);
  const withoutParent =
    parentCode && !selected.includes(code)
      ? next.filter((candidate) => candidate !== parentCode)
      : next;

  return withCodes(params, "category", withoutParent);
}

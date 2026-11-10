import { resolvePlural } from "./plural";

export type TranslateParams = Record<string, string | number>;

function lookup(
  bundle: Record<string, string>,
  tag: string,
  key: string,
  params?: TranslateParams,
): string {
  const count = params?.count;
  const text =
    typeof count === "number"
      ? resolvePlural(bundle, key, count, tag)
      : bundle[key];
  return text ?? key;
}

function interpolate(text: string, params?: TranslateParams): string {
  return Object.entries(params ?? {}).reduce(
    (value, [name, replacement]) =>
      value.replaceAll(`{${name}}`, String(replacement)),
    text,
  );
}

/** Look `key` up in `bundle` (plural-aware when `params.count` is a number) and fill `{name}` slots. */
export function translate(
  bundle: Record<string, string>,
  tag: string,
  key: string,
  params?: TranslateParams,
): string {
  return interpolate(lookup(bundle, tag, key, params), params);
}

import { pluralCategories } from "../i18n/plural";
import { intlTag } from "../i18n/localeMeta";

export type Bundle = Record<string, string>;

const PLURAL_SUFFIX = /_(zero|one|two|few|many|other)$/;
const PLACEHOLDER = /\{(\w+)\}/g;

/** Placeholder names in `text`, sorted and without repeats. */
export function placeholders(text: string): string[] {
  const names = [...text.matchAll(PLACEHOLDER)].map((match) => match[1]);
  return [...new Set(names)].sort();
}

/** Base keys of plural families: `x_other` counts when plain `x` is not itself a key. */
function familyBases(bundle: Bundle): Set<string> {
  const bases = Object.keys(bundle)
    .filter((key) => key.endsWith("_other"))
    .map((key) => key.replace(PLURAL_SUFFIX, ""))
    .filter((base) => !(base in bundle));
  return new Set(bases);
}

/** Keys with plural forms collapsed to their base key (`n_one`, `n_few` both give `n`). */
function collapsedKeys(bundle: Bundle): Set<string> {
  const bases = familyBases(bundle);
  return new Set(
    Object.keys(bundle).map((key) => {
      const base = key.replace(PLURAL_SUFFIX, "");
      return bases.has(base) ? base : key;
    }),
  );
}

function missing(from: Set<string>, into: Set<string>): string[] {
  return [...from].filter((key) => !into.has(key)).sort();
}

function keySetProblems(locale: string, bundle: Bundle, en: Bundle): string[] {
  const [have, want] = [collapsedKeys(bundle), collapsedKeys(en)];
  return [
    ...missing(want, have).map((key) => `${locale}: missing key ${key}`),
    ...missing(have, want).map((key) => `${locale}: extra key ${key}`),
  ];
}

/** The `en` form to compare a form against: the same category, else its `_other`. */
function referenceText(en: Bundle, key: string): string | undefined {
  return en[key] ?? en[key.replace(PLURAL_SUFFIX, "_other")];
}

function placeholderProblems(
  locale: string,
  bundle: Bundle,
  en: Bundle,
): string[] {
  return Object.entries(bundle).flatMap(([key, text]) => {
    const reference = referenceText(en, key);
    if (reference === undefined) return [];
    const [got, want] = [placeholders(text), placeholders(reference)];
    return got.join() === want.join()
      ? []
      : [`${locale}: ${key} has placeholders {${got}} but en has {${want}}`];
  });
}

function pluralProblems(locale: string, bundle: Bundle): string[] {
  const needed = pluralCategories(intlTag(locale));
  return [...familyBases(bundle)].flatMap((base) =>
    needed
      .filter((category) => !(`${base}_${category}` in bundle))
      .map((category) => `${locale}: ${base} lacks plural form ${category}`),
  );
}

/** Every way `locales` drifts from `en`: key sets, `{placeholder}` names and plural forms. */
export function parityProblems(locales: Record<string, Bundle>): string[] {
  const { en, ...others } = locales;
  const vsEn = Object.entries(others).flatMap(([locale, bundle]) => [
    ...keySetProblems(locale, bundle, en),
    ...placeholderProblems(locale, bundle, en),
  ]);
  const plurals = Object.entries(locales).flatMap(([locale, bundle]) =>
    pluralProblems(locale, bundle),
  );
  return [...vsEn, ...plurals];
}

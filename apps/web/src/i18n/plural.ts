/**
 * Plural-aware key lookup for `t(key, { count })`.
 *
 * A count resolves `${key}_${category}` first, where the category is what
 * `Intl.PluralRules` selects for the locale, then `${key}_other`, then `key`.
 * The categories a locale needs come from `Intl`, never from a list here:
 * `ru` and `pl` need one/few/many/other, `ro` one/few/other, `tr` and `en`
 * one/other.
 *
 * Copy guidance: do not interpolate nouns into sentences. Slavic languages
 * inflect a noun by case, so `"{count} {noun}"` and `"in {place}"` cannot be
 * translated; write whole-phrase keys per plural form instead.
 */

/** The plural categories `tag` distinguishes, from `Intl.PluralRules`. */
export function pluralCategories(tag: string): readonly string[] {
  return new Intl.PluralRules(tag).resolvedOptions().pluralCategories;
}

/** Keys to try for `count`, most specific first. */
function candidateKeys(key: string, count: number, tag: string): string[] {
  const category = new Intl.PluralRules(tag).select(count);
  return [`${key}_${category}`, `${key}_other`, key];
}

/** The first stored form for `count`, or undefined when no key in the chain exists. */
export function resolvePlural(
  bundle: Record<string, string>,
  key: string,
  count: number,
  tag: string,
): string | undefined {
  return candidateKeys(key, count, tag)
    .map((candidate) => bundle[candidate])
    .find((text) => text !== undefined);
}

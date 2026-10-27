/** The translation of ``key``, or ``raw`` when no string exists (an unknown value stays readable). */
export function translateOrRaw(
  t: (key: string) => string,
  key: string,
  raw: string,
): string {
  const label = t(key);
  return label === key ? raw : label;
}
